from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging

logger = logging.getLogger("GatewayMetrics")

# Define Prometheus metrics collectors
ORDERS_SENT_TOTAL = Counter(
    "fix_gateway_orders_sent_total",
    "Total number of orders successfully routed to the exchange",
    ["symbol", "side"]
)

RISK_REJECTIONS_TOTAL = Counter(
    "fix_gateway_risk_rejections_total",
    "Total number of orders blocked by the pre-trade risk engine",
    ["reason"]
)

ROUNDTRIP_LATENCY_SECONDS = Histogram(
    "fix_gateway_roundtrip_latency_seconds",
    "Round-trip execution latency from order submission to execution report",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

SESSION_STATUS = Gauge(
    "fix_gateway_session_connected",
    "FIX session connectivity status (1 = Connected, 0 = Disconnected)"
)

def start_metrics_server(port: int = 8000):
    """Starts the HTTP metrics server for Prometheus scraping."""
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
