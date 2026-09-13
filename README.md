# Institutional Execution Gateway & FIX Protocol Engine

A low-latency, resilient Python FIX (Financial Information eXchange) execution gateway engineered with real-time pre-trade risk controls, sequence gap management, durable session persistence, automatic network reconnection, background heartbeats, and automated CI/CD pipeline validation.

## 🚀 Key Architectural Features

* **Modular Package Layout (`src/`):** Clean separation of concerns featuring dedicated components for session management (`FIXHandler`), risk evaluation (`PreTradeRiskEngine`), state durability (`DurableSequenceStore`), and remote exchange simulation (`MockExchangeAcceptor`).
* **Pre-Trade Risk Controls:** Real-time validation checks enforcing maximum order size volumes (MW), monetary notional thresholds, velocity-based rate limiting, and an emergency master kill-switch.
* **Institutional Resilience & State Persistence:** Automatic TCP reconnection with exponential backoff, background heartbeat maintenance (`35=0`), sequence gap detection, and JSON-based durable sequence store recovery across session restarts.
* **Automated CI/CD Pipeline:** Integrated GitHub Actions workflow running automated unit and integration test suites on every push and pull request.

---

## 🛠️ Project Structure

```text
Institutional-execution-gateway/
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI pipeline configuration
├── src/
│   ├── fix_handler.py         # Core FIX protocol state, checksums, heartbeats & sequence management
│   ├── gateway.py             # Institutional Gateway orchestrator & Pre-Trade Risk Engine
│   └── mock_acceptor.py       # Asynchronous mock exchange matching engine for integration testing
├── tests/
│   ├── test_compliance.py     # Protocol compliance and message structure checks
│   ├── test_fix_handler.py    # Unit tests for sequence tracking, checksums, and risk thresholds
│   └── test_integration.py    # End-to-end loopback socket execution tests
├── requirements.txt           # Project dependencies (pytest, pytest-asyncio)
└── README.md
