# Institutional Execution Gateway & Multi-Leg Hedging Engine

## Overview

This repository provides a lightweight, low-latency asynchronous execution and risk-hedging framework designed specifically for power and spot trading desks. It addresses critical market friction points—such as systemic shocks caused by sudden interconnector trips (e.g., IGA supply swings) and the manual re-pricing delays that result in undefined leg-risk slippage.

## Core Architecture

* **Event-Driven Telemetry Listener:** Ingests order book updates asynchronously to bypass visual terminal lag and interface bottlenecks.
* **Dynamic Spread & Volatility Triggers:** Automatically tracks threshold blowouts and flags market dislocations in real time.
* **Automated Multi-Leg Rebalancing:** Instantly calculates partial fills and dispatches aggressive hedging orders to offsetting legs to lock down exposure before manual intervention is required.
* **Decoupled Configuration Layer:** Uses external JSON configuration mappings (`config.json`) allowing the engine to adapt seamlessly across disparate exchange stacks or terminal environments.

## Testing & Performance Benchmarking

The repository includes a comprehensive unit test suite covering FIX message parsing, checksum generation, sequence gap detection, and state durability.

To run the test suite locally with `pytest`:

```bash
PYTHONPATH=. pytest tests/ -v
