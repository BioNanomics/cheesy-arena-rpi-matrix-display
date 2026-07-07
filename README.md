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
```
(Note: Use sudo apt install python3-websocket if your OS enforces externally managed environments).

## ⚙️ Configuration
Open the fms_test.py file and edit the top variables to match your field network:
```Python
FMS_IP = "10.0.100.5"   # The IP address of your Cheesy Arena Server
TARGET_STATION = "B1"   # The Alliance Station you want to monitor (e.g., R1, B2, Timer)
```
## ▶️ Usage
Make sure your computer or Raspberry Pi is connected to the field network, then run the script:
```bash
python3 fms_test.py
```
You should see a successful handshake, followed by live data printing to your screen whenever the scorekeeper updates the match or a driver station is plugged in:
```Plaintext
Successfully connected to Cheesy Arena at ws://10.0.100.5:8080/displays/alliance_station/websocket?displayId=100&station=B1
Listening for updates on station: B1...

--- FMS UPDATE ---
Station: B1
Team:    9431 (The Gold Standard)
Status:  CONNECTED [O]
------------------
```
## 🔮 Next Steps (Phase 2)
This code currently prints to the console, but the overarching goal of this repository is to replace the print() statements with the rpi-rgb-led-matrix library. We will map this live data directly onto massive physical P10 LED panels to create custom, less expensive driver station signs than what is currently being sold.
