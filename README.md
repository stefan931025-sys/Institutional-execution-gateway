# Institutional Execution Gateway

[![CI Pipeline](https://github.com/stefan931025-sys/Institutional-execution-gateway/actions/workflows/ci.yml/badge.svg)](https://github.com/stefan931025-sys/Institutional-execution-gateway/actions/workflows/ci.yml)

![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg) ![Docker](https://img.shields.io/badge/docker-enabled-blue.svg) ![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

An automated institutional execution gateway and FIX protocol client designed to handle order routing, simulation, and risk-managed transaction workflows. Integrated with CI/CD pipelines via GitHub Actions for continuous validation and execution testing.

## Features

* **FIX Protocol Client:** Establishes secure socket connections, handles session initialization/sequence tracking, and manages logon handshakes.
* **Order Lifecycle Management:** Automates the generation, transmission, and processing of `New Order - Single` messages alongside execution report tracking (`Status=0` for Accepted, `Status=2` for Filled).
* **Automated CI/CD Pipeline:** Uses GitHub Actions to spin up an exchange simulator and execute end-to-end integration tests on every push.

## Configuration & Secrets

The pipeline securely injects environment parameters and endpoint hosts at runtime using GitHub Actions Secrets.

## Repository Structure

```text
Institutional-execution-gateway/
├── .github/workflows/ci.yml # CI workflow pipeline
├── src/                      # Gateway source & execution engines
├── tests/                    # Integration & test utility suite
├── Dockerfile                # Single-stage container configuration
├── Multi-stage dockerfile    # Multi-stage release container build
├── config.json               # Gateway network configuration
├── exchange_simulator.py     # Local FIX exchange simulator engine
├── execution_algos.py        # Order routing execution algorithms
├── fix_socket_client.py      # Core FIX protocol client implementation
├── main.py                   # Entry point execution service
├── risk_manager.py           # Pre-trade risk controls & validation
└── requirements.txt          # Python dependencies
