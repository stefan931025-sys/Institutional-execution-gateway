from prometheus_client import Counter, Gauge, Histogram

# Prometheus Counter automatically appends '_total', so define the base name cleanly
RISK_REJECTIONS_TOTAL = Counter(
    'fix_gateway_risk_rejections', 
    'Total number of orders rejected by pre-trade risk engine', 
    ['reason']
)

ORDERS_SENT_TOTAL = Counter(
    'fix_gateway_orders_sent', 
    'Total number of orders successfully sent to exchange', 
    ['symbol', 'side']
)

SESSION_STATUS = Gauge(
    'fix_gateway_session_status', 
    'FIX session connection status (1 = Connected, 0 = Disconnected)'
)

ROUNDTRIP_LATENCY_SECONDS = Histogram(
    'fix_gateway_roundtrip_latency_seconds', 
    'Roundtrip order processing and submission latency'
)
