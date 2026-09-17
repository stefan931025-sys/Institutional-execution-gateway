# Institutional Execution Gateway

An automated institutional execution gateway and FIX protocol client designed to handle order routing, simulation, and risk-managed transaction workflows. Integrated with CI/CD pipelines via GitHub Actions for continuous validation and execution testing.

## Features
* **FIX Protocol Client:** Establishes secure socket connections, handles session initialization/sequence tracking, and manages logon handshakes.
* **Order Lifecycle Management:** Automates the generation, transmission, and processing of `New Order Single` messages alongside execution report tracking (`Status=0` for Accepted, `Status=2` for Filled).
* **Automated CI/CD Pipeline:** Uses GitHub Actions to spin up an exchange simulator and execute end-to-end integration tests on every push.

## Configuration & Secrets
The pipeline securely injects environment parameters and endpoint hosts at runtime using GitHub Actions Secrets.

* **`FIX_SERVER_HOST`**: Configured as a repository secret to map the target FIX server or forwarded endpoint securely during CI runs.

## Local Development & Testing

1. Clone the repository and install dependencies:
   ```bash
   git clone [https://github.com/stefan931025-sys/Institutional-execution-gateway.git](https://github.com/stefan931025-sys/Institutional-execution-gateway.git)
   cd Institutional-execution-gateway
   pip install -r requirements.txt
