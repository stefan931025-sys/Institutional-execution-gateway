import asyncio
import json
import logging
import os
from typing import Dict, Any, Callable

logger = logging.getLogger("FIXHandler")

class AsyncFIXHandler:
    def __init__(self, host: str, port: int, sender_comp_id: str, target_comp_id: str, state_file: str = "fix_state.json"):
        self.host = host
        self.port = port
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.state_file = state_file
        
        # Load persisted sequence numbers or initialize to 1
        self.inbound_seq_num, self.outbound_seq_num = self._load_session_state()
        
        self.reader = None
        self.writer = None
        self.is_connected = False
        self.heartbeat_interval = 30  # Default 30 seconds
        self.heartbeat_task = None

    def _load_session_state(self) -> tuple[int, int]:
        """Persists and recovers sequence numbers to prevent exchange session rejections on restart."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    logger.info(f"Loaded session state: InboundSeq={data.get('inbound', 1)}, OutboundSeq={data.get('outbound', 1)}")
                    return data.get("inbound", 1), data.get("outbound", 1)
            except Exception as e:
                logger.warning(f"Failed to load state file, resetting sequences to 1: {e}")
        return 1, 1

    def _save_session_state(self):
        """Saves current sequence numbers to disk."""
        try:
            data = {
                "inbound": self.inbound_seq_num,
                "outbound": self.outbound_seq_num
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")

    async def connect(self):
        """Establish persistent TCP connection with the exchange gateway."""
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.is_connected = True
            logger.info(f"Connected to FIX Gateway endpoint at {self.host}:{self.port}")
            await self._send_logon()
            
            # Launch active background heartbeat task once connected
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        except Exception as e:
            logger.error(f"Failed to connect to FIX endpoint: {e}")
            self.is_connected = False

    def _format_fix_message(self, msg_type: str, fields: Dict[int, Any]) -> bytes:
        """Constructs a raw FIX message payload with persistent sequence numbering and checksums."""
        body_parts = [
            f"35={msg_type}",
            f"49={self.sender_comp_id}",
            f"56={self.target_comp_id}",
            f"34={self.outbound_seq_num}"
        ]
        
        for tag, val in fields.items():
            body_parts.append(f"{tag}={val}")
            
        body = "\x01".join(body_parts) + "\x01"
        header = f"8=FIX.4.2\x019={len(body)}\x01"
        raw_msg = header + body
        
        checksum = sum(raw_msg.encode('ascii')) % 256
        full_message = f"{raw_msg}10={checksum:03d}\x01"
        
        # Increment and persist outbound sequence number
        self.outbound_seq_num += 1
        self._save_session_state()
        
        return full_message.encode('ascii')

    async def _send_logon(self):
        """Dispatches the mandatory FIX Logon sequence (MsgType = A)."""
        logon_fields = {
            98: 0,                   # EncryptMethod: None
            108: self.heartbeat_interval  # HeartBtInt: heartbeat frequency
        }
        msg = self._format_fix_message("A", logon_fields)
        self.writer.write(msg)
        await self.writer.drain()
        logger.info("Sent FIX Logon sequence with active session state tracking.")

    async def _heartbeat_loop(self):
        """Active background loop ensuring socket stays alive during idle periods (MsgType = 0)."""
        try:
            while self.is_connected:
                await asyncio.sleep(self.heartbeat_interval)
                if self.is_connected and self.writer:
                    hb_msg = self._format_fix_message("0", {})
                    self.writer.write(hb_msg)
                    await self.writer.drain()
                    logger.debug("Dispatched periodic FIX Heartbeat (MsgType=0).")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")

    async def send_order(self, symbol: str, side: str, qty: float, price: float):
        """Translates an internal hedge trigger into a FIX New Order - Single (MsgType = D)."""
        side_code = '1' if side.upper() == 'BUY' else '2'
        
        order_fields = {
            11: f"CLORD-{int(asyncio.get_event_loop().time() * 1000)}", 
            55: symbol,                                                 
            54: side_code,                                              
            38: qty,                                                    
            40: '2',                                                    
            44: price,                                                  
            59: '0'                                                     
        }
        
        msg = self._format_fix_message("D", order_fields)
        if self.writer and self.is_connected:
            self.writer.write(msg)
            await self.writer.drain()
            logger.info(f"FIX NewOrderSingle dispatched [Symbol: {symbol}, Side: {side}, Qty: {qty}, Price: {price}]")

    async def listen_loop(self, on_fill_callback: Callable[[str, float, float], Any]):
        """Asynchronously parses incoming byte stream, validates sequence gaps, and routes execution reports."""
        buffer = b""
        while self.is_connected:
            try:
                data = await self.reader.read(4096)
                if not data:
                    logger.warning("Connection closed by exchange FIX gateway.")
                    break
                buffer += data
                
                while b"\x01" in buffer:
                    parts = buffer.split(b"\x01")
                    raw_msg = b"\x01".join(parts[:len(parts)-1]) + b"\x01"
                    buffer = parts[-1] + b"\x01" 
                    
                    fields = {}
                    for item in raw_msg.split(b"\x01"):
                        if b"=" in item:
                            k, v = item.split(b"=", 1)
                            try:
                                fields[int(k)] = v.decode('ascii')
                            except ValueError:
                                continue
                                
                    if not fields:
                        continue

                    # Validate sequence numbers (Tag 34)
                    msg_seq_num = int(fields.get(34, self.inbound_seq_num))
                    if msg_seq_num > self.inbound_seq_num:
                        logger.warning(f"Sequence gap detected! Expected {self.inbound_seq_num}, received {msg_seq_num}.")
                        # Production systems would fire a ResendRequest (Tag 35=2) here.
                    
                    self.inbound_seq_num = msg_seq_num + 1
                    self._save_session_state()

                    msg_type = fields.get(35)
                    
                    # Handle incoming Heartbeats or Test Requests automatically
                    if msg_type == '1':  # TestRequest
                        test_req_id = fields.get(112, "")
                        resp_msg = self._format_fix_message("0", {112: test_req_id})
                        self.writer.write(resp_msg)
                        await self.writer.drain()
                    
                    # Handle Execution Reports (MsgType = 8)
                    elif msg_type == '8':
                        exec_type = fields.get(150) 
                        cl_ord_id = fields.get(11)  
                        cum_qty = float(fields.get(14, 0.0)) 
                        avg_px = float(fields.get(6, 0.0))   
                        
                        logger.info(f"FIX Execution Report [ClOrdID: {cl_ord_id}, ExecType: {exec_type}, CumQty: {cum_qty}, AvgPx: {avg_px}]")
                        
                        if exec_type in ('1', '2'): 
                            await on_fill_callback(cl_ord_id, cum_qty, avg_px)
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error encountered in FIX listen loop: {e}")
                break

    async def close(self):
        """Closes the background tasks and network connection cleanly."""
        self.is_connected = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            logger.info("FIX session terminated gracefully and state persisted.")
