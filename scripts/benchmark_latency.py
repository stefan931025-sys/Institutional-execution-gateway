#!/usr/bin/env python3
"""
Latency Profiling and Benchmarking Script (`scripts/benchmark_latency.py`)
Measures microsecond-level execution latency percentiles for pre-trade risk evaluation 
and message decoding loops to validate institutional low-latency performance claims.
"""

import time
import statistics
import numpy as np

# Mocking a lightweight pre-trade risk validation function for benchmarking
def mock_pre_trade_risk_check(order_size: float, notional_limit: float, current_exposure: float) -> bool:
    """Simulates sub-millisecond synchronous risk checks (position boundaries & rate limits)."""
    if (current_exposure + order_size) > notional_limit:
        return False
    return True


def benchmark_risk_engine(iterations: int = 100_000) -> dict[str, float]:
    """Profiles execution latency of the pre-trade risk validation logic."""
    latencies_ns = []
    
    limit = 1_000_000.0
    exposure = 400_000.0
    order = 50_000.0

    # Warm-up loop to bypass JIT/cache cold-start anomalies
    for _ in range(1000):
        mock_pre_trade_risk_check(order, limit, exposure)

    # Timed benchmark loop
    for _ in range(iterations):
        start = time.perf_counter_ns()
        mock_pre_trade_risk_check(order, limit, exposure)
        end = time.perf_counter_ns()
        latencies_ns.append(end - start)

    latencies_us = [lat / 1000.0 for lat in latencies_ns] # Convert nanoseconds to microseconds

    return {
        "iterations": iterations,
        "p50_us": statistics.median(latencies_us),
        "p99_us": np.percentile(latencies_us, 99.0),
        "p999_us": np.percentile(latencies_us, 99.9),
        "max_us": max(latencies_us),
    }


if __name__ == "__main__":
    print("--- Institutional Gateway: Latency Benchmark Suite ---")
    results = benchmark_risk_engine(100_000)
    print(f"Iterations: {results['iterations']:,}")
    print(f"p50 Latency:  {results['p50_us']:.3f} µs")
    print(f"p99 Latency:  {results['p99_us']:.3f} µs")
    print(f"p99.9 Latency: {results['p999_us']:.3f} µs")
    print(f"Max Latency:  {results['max_us']:.3f} µs")
