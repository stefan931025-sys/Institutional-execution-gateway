import asyncio
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ExchangeSimulator")

class MockExchangeServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 9800):
        self.host = host
        self.port = port
        self.out_seq_num = 1
        self.in_seq_num = 1
        self.target_comp_id = "CLIENT_SIM"
        self.sender_comp_id = "EXCHANGE_SIM"

    def _calculate_checksum(self, message: str) -> str:
        """Calculate standard FIX checksum."""
        checksum = sum(ord(char) for char in message) % 256
        return f"{checksum:03d}"

    def build_message(self, msg_type: str, fields: dict) -> bytes:
        """Construct a framed FIX message with SOH delimiters."""
        body_parts = []
        for tag, val in fields.items():
            body_parts.append(f"{tag}={val}")
        
        body = "\x01".join(body_parts) + "\x01"
        now_utc = datetime.now(timezone.utc).strftime("%Y%m%d-%H:%M:%S.%f")[:-3]
        
        header_base = (
            f"8=FIX.4.2\x01"
            f"9={len(body)}\x01"
            f"35={msg_type}\x01"
            f"49={self.sender_comp_id}\x01"
            f"56={self.target_comp_id}\x01"
            f"34={self.out_seq_num}\x01"
            f"52={now_utc}\x01"
        )
        
        raw_msg_without_trailer = header_base + body
        checksum_str = self._calculate_checksum(raw_msg_without_trailer)
        full_message = raw_msg_without_trailer + f"10={checksum_str}\x01"
        
        self.out_seq_num += 1
        return full_message.encode("ascii")

    def parse_message(self, raw_data: str) -> dict:
        """Parse raw FIX string into a tag-value dictionary."""
        fields = {}
        pairs = raw_data.split("\x01")
        for pair in pairs:
            if "=" in pair:
                tag, val = pair.split("=", 1)
                fields[int(tag)] = val
        return fields

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle individual client session lifecycle and message routing."""
        peername = writer.get_extra_info('peername')
        logger.info(f"Client connected from {peername}")

        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    logger.warning("Client disconnected.")
                    break

                raw_str = data.decode("ascii", errors="ignore")
                messages = raw_str.split("10=")
                for msg in messages[:-1]:
                    full_msg = msg + "10=" + messages[messages.index(msg) + 1][:3] + "\x01"
                    fields = self.parse_message(full_msg)
                    msg_type = fields.get(35)
                    seq_num = fields.get(34)
                    
                    logger.info(f"Received [MsgType={msg_type}, Seq={seq_num}] from client")

                    # Handle Logon (MsgType=A)
                    if msg_type == "A":
                        logon_resp = self.build_message("A", {"98": "0", "108": "30"})
                        writer.write(logon_resp)
                        await writer.drain()
                        logger.info("Sent Logon confirmation.")

                    # Handle Heartbeat (MsgType=0) or TestRequest (MsgType=1)
                    elif msg_type == "0":
                        logger.info("Processed client Heartbeat.")
                    elif msg_type == "1":
                        test_req_id = fields.get(112)
                        hb_resp = self.build_message("0", {"112": test_req_id} if test_req_id else {})
                        writer.write(hb_resp)
                        await writer.drain()
                        logger.info("Responded to TestRequest with Heartbeat.")

                    # Handle NewOrderSingle (MsgType=D) -> Fire back ExecutionReport (MsgType=8)
                    elif msg_type == "D":
                        cl_ord_id = fields.get(11)
                        symbol = fields.get(55, "UNKNOWN")
                        side = fields.get(54)
                        order_qty = fields.get(38)
                        price = fields.get(44, "0")

                        logger.info(f"NewOrderSingle received: ClOrdID={cl_ord_id}, Symbol={symbol}, Qty={order_qty}")

                        # Send ExecutionReport - New (OrdStatus=0)
                        exec_report_new = self.build_message("8", {
                            "37": f"EXCH_ID_{cl_ord_id}",  # OrderID
                            "11": cl_ord_id,
                            "17": f"EXEC_{self.out_seq_num}",  # ExecID
                            "150": "0",  # ExecType (0 = New)
                            "39": "0",  # OrdStatus (0 = New)
                            "55": symbol,
                            "54": side,
                            "38": order_qty,
                            "44": price,
                            "151": order_qty,  # LeavesQty
                            "14": "0"   # CumQty
                        })
                        writer.write(exec_report_new)
                        await writer.drain()

                        # Simulate immediate fill after brief pause (ExecType=2, OrdStatus=2 -> Filled)
                        await asyncio.sleep(0.1)
                        exec_report_fill = self.build_message("8", {
                            "37": f"EXCH_ID_{cl_ord_id}",
                            "11": cl_ord_id,
                            "17": f"EXEC_{self.out_seq_num}",
                            "150": "2",  # ExecType (2 = Fill)
                            "39": "2",  # OrdStatus (2 = Filled)
                            "55": symbol,
                            "54": side,
                            "38": order_qty,
                            "44": price,
                            "6": price,  # AvgPx
                            "151": "0",  # LeavesQty
                            "14": order_qty  # CumQty
                        })
                        writer.write(exec_report_fill)
                        await writer.drain()
                        logger.info(f"Simulated full execution report sent for ClOrdID={cl_ord_id}")

        except Exception as e:
            logger.error(f"Error handling client session: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info("Connection closed.")

    async def start(self):
        """Start the TCP server."""
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        logger.info(f"Mock Exchange Simulator running on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    simulator = MockExchangeServer()
    try:
        asyncio.run(simulator.start())
    except KeyboardInterrupt:
        logger.info("Simulator stopped by user.")
