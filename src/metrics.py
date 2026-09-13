from prometheus_client import Counter, Gauge, Histogram

# Counter base name 'fix_gateway_risk_rejections' automatically appends '_total' 
# resulting in 'fix_gateway_risk_rejections_total' as queried by the test.
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

# Aligned with test expectation: 'fix_gateway_session_connected'
SESSION_STATUS = Gauge(
    'fix_gateway_session_connected', 
    'FIX session connection status (1 = Connected, 0 = Disconnected)'
)

ROUNDTRIP_LATENCY_SECONDS = Histogram(
    'fix_gateway_roundtrip_latency_seconds', 
    'Roundtrip order processing and submission latency'
)
