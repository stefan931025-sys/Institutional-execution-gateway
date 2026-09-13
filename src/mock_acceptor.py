import asyncio
import logging

logger = logging.getLogger("MockAcceptor")

class MockExchangeAcceptor:
    """Simulates a remote FIX exchange matching engine for integration testing."""
    def __init__(self, host: str = "127.0.0.1", port: int = 9800):
        self.host = host
        self.port = port
        self.server = None
        self.client_writer = None

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.client_writer = writer
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                message = data.decode()
                logger.info(f"Mock Acceptor received: {message.strip()}")

                # Simple response simulation based on MsgType (tag 35)
                if "35=A" in message:  # Logon
                    response = "8=FIX.4.2\x019=45\x0135=A\x0134=1\x0149=EXCHANGE_SIM\x0156=CLIENT_SIM\x0198=0\x01108=30\x0110=181\x01"
                    writer.write(response.encode())
                    await writer.drain()
                elif "35=D" in message:  # New Order Single -> Send Execution Report (35=8)
                    exec_report = "8=FIX.4.2\x019=65\x0135=8\x0134=2\x0149=EXCHANGE_SIM\x0156=CLIENT_SIM\x0137=ORDER_123\x01150=0\x0139=0\x0110=152\x01"
                    writer.write(exec_report.encode())
                    await writer.drain()
        except asyncio.CancelledError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self):
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        logger.info(f"Mock Exchange Acceptor listening on {self.host}:{self.port}")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
