# Institutional Execution Gateway

A robust, asynchronous **Financial Information eXchange (FIX) Protocol** client and execution gateway built in Python. Designed for low-latency, resilient connectivity and strict state tracking, this system bridges trading applications with FIX-compliant exchange sandboxes.

---

## 🏗️ Core Architecture & Components

The gateway is built using modern asynchronous Python (`asyncio`) and structured around institutional systems engineering principles:

* **`fix_socket_client.py` (The Socket & Protocol Layer):** Manages TCP socket connections, FIX message formatting, checksum calculation (`Tag 10`), session logons (`35=A`), order submission (`35=D`), and background heartbeats (`35=0`).
* **`database.py` (Persistence & State Layer):** Powered by `aiosqlite` for non-blocking asynchronous database operations. It ensures absolute sequence number durability (`Tag 34`) across application restarts and tracks local order execution states.
* **`main.py` (The Execution Runner):** Manages the concurrency lifecycle, cleanly orchestrating asynchronous background routines, connection handshakes, and graceful shutdowns.

---

## ⚙️ Key Technical Features

1. **Robust TCP Stream Framing & Buffering:** 
   * TCP is a stream-oriented protocol, meaning packets can fragment, merge, or arrive partially. 
   * The client utilizes a persistent `bytearray` stream buffer to continuously scan, isolate, and safely parse incoming frames bounded by `8=FIX` and the checksum trailer (`10=XXX\x01`), completely preventing malformed packet crashes.
2. **Session Durability & Sequence Integrity:**
   * Automatically loads and updates inbound and outbound sequence numbers from an isolated SQLite database on every transaction. Prevents critical session desynchronization faults.
3. **Graceful Lifecycle Management:**
   * Implements strict error visibility and clean cancellation patterns (`try...finally`) to prevent orphaned background heartbeat or listener loops.

---

## 🚀 Quick Start

### 1. Prerequisites
Ensure you are running Python 3.10+ and have your environment set up.

### 2. Install Dependencies
Install the required asynchronous SQLite package:
```bash
pip install -r requirements.txt
