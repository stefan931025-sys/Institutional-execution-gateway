from prometheus_client import Counter, Histogram, start_http_server
import logging

logger = logging.getLogger("GatewayMetrics")

# Define Prometheus metrics
ORDER_COUNTER = Counter(
    "gateway_orders_total", 
    "Total number of orders processed", 
    ["status", "symbol"]
)

LATENCY_HISTOGRAM = Histogram(
    "gateway_execution_latency_seconds", 
    "End-to-end order execution and fill latency"
)

RISK_REJECTIONS = Counter(
    "gateway_risk_rejections_total", 
    "Total orders blocked by the pre-trade risk engine", 
    ["reason_code"]
)

def start_metrics_server(port: int = 9090):
    """Starts the Prometheus metrics HTTP endpoint."""
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics exporter live on port {port}/metrics")
    except Exception as e:
        logger.error(f"Failed to start Prometheus metrics server: {e}")
