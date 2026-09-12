# Institutional Execution Gateway

A production-grade, low-latency asynchronous execution gateway engineered for power and spot trading markets. Built with strict pre-trade risk controls, institutional resilience (sequence gap handling & durable state recovery), real-time Prometheus telemetry, and advanced algorithmic order slicing.

## 🚀 Key Architectural Highlights

*   **Asynchronous Core:** Powered by Python's `asyncio` and `uvloop` for high-throughput, low-latency message processing.
*   **FIX Protocol Engine:** Implements robust session management, checksum validation, SOH-delimited message parsing, and automated sequence gap detection/resend requests.
*   **Pre-Trade Risk Management Engine:** Hardens execution safety with real-time gates for:
    *   Maximum MW order size boundaries.
    *   Notional value limits (GBP/USD).
    *   Velocity rate-limiting (messages per second flood protection).
    *   Instantaneous Master Kill Switch.
*   **Institutional Resilience & State Persistence:** Features a durable JSON/disk-backed sequence store to ensure active session states survive unexpected restarts or system crashes.
*   **Observability & Telemetry:** Integrated `prometheus-client` exporters exposing real-time order counters, risk rejection error codes, and execution latency histograms.
*   **Advanced Execution Algorithms:** Includes an **Iceberg / TWAP Slicer** to break down large parent block orders into hidden child slices over timed intervals, minimizing market impact during liquidity shocks.

---

## 🛠️ Tech Stack

*   **Language:** Python 3.10+
*   **Networking/Concurrency:** `asyncio`, `uvloop`
*   **Testing:** `pytest`, `pytest-asyncio`
*   **Monitoring:** `prometheus-client` (Port `9090`)
*   **Containerization:** Multi-stage `Dockerfile` (optimized for slim runtime images)
*   **CI/CD:** GitHub Actions automated testing pipelines

---

## 📁 Repository Structure

```text
Institutional-execution-gateway/
│
├── gateway.py              # Main asynchronous execution orchestrator & risk engine
├── fix_handler.py          # FIX protocol handler, session logic, and durable store
├── execution_algos.py      # Advanced execution algorithms (Iceberg/TWAP Slicer)
├── metrics.py              # Prometheus telemetry and metrics exporters
├── requirements.txt        # Production and testing dependencies
├── Dockerfile              # Multi-stage production container build
├── .github/
│   └── workflows/
│       └── ci.yml          # GitHub Actions automated CI test pipeline
└── tests/
    ├── test_fix_handler.py # Unit tests, state persistence, and performance benchmarks
    └── test_compliance.py  # Exchange session compliance and logon verification
