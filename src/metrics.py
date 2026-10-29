import logging
from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger("GatewayMetrics")

# --- Counters & Gauges ---
RISK_REJECTIONS_TOTAL = Counter(
    "fix_gateway_risk_rejections_total",
    "Total number of orders rejected by pre-trade risk engine",
    ["reason"],
)

ORDERS_SENT_TOTAL = Counter(
    "fix_gateway_orders_sent_total",
    "Total number of orders successfully sent to exchange",
    ["symbol", "side"],
)

SESSION_STATUS = Gauge(
    "fix_gateway_session_connected",
    "FIX session connection status (1 = Connected, 0 = Disconnected)",
)

ROUNDTRIP_LATENCY_SECONDS = Histogram(
    "fix_gateway_roundtrip_latency_seconds",
    "Roundtrip order processing and submission latency",
)

ORDER_COUNTER = Counter(
    "gateway_orders_total",
    "Total number of orders processed",
    ["status", "symbol"],
)

LATENCY_HISTOGRAM = Histogram(
    "gateway_execution_latency_seconds",
    "End-to-end order execution and fill latency",
)

RISK_REJECTIONS = Counter(
    "gateway_risk_rejections_total",
    "Total orders blocked by the pre-trade risk engine",
    ["reason_code"],
)


def start_metrics_server(port: int = 9090) -> None:
    """Starts the Prometheus metrics HTTP endpoint."""
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics exporter live on port {port}/metrics")
    except Exception as e:
        logger.error(f"Failed to start Prometheus metrics server: {e}")
