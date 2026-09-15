## 🚀 Quickstart: Local Execution in 60 Seconds

Test the asynchronous FIX gateway and simulated exchange locally using Python:

* **Step 1:** Clone and install dependencies
  - `git clone https://github.com/stefan931025-sys/Institutional-execution-gateway.git`
  - `cd Institutional-execution-gateway`
  - `pip install -r requirements.txt`

* **Step 2:** Spin up the mock exchange simulator
  - `python exchange_simulator.py`

* **Step 3:** Run the gateway client & execution pipeline
  - `python main.py`
