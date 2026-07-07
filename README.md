# Cheesy Arena WebSocket Console Monitor (Phase 1 Prototype)

This is a lightweight Python script that taps directly into the [Cheesy Arena](https://github.com/Team254/cheesy-arena) Field Management System (FMS) via WebSockets and streams live match data straight to your terminal. 

This script serves as a **software test bench**. It proves that its possible to successfully parse live FMS data (like team assignments and driver station connection statuses) without relying on a web browser, paving the way for custom LED matrix field displays.

## 🚀 Features
* **Direct WebSocket Connection:** Listens to the exact same live stream that the official FMS auxiliary displays use.
* **Terminal Output:** Prints real-time team assignments, nicknames, and driver station connection statuses directly to the console.
* **Auto-Reconnect:** If the FMS server drops or reboots, the script automatically attempts to re-establish the handshake.
* **Lightweight:** Runs entirely in the terminal with zero GUI or web browser overhead.

## 💻 Prerequisites
You only need Python 3 and the WebSocket client library. 
To install the required dependency on a Raspberry Pi, run:

```bash
pip3 install websocket-client
