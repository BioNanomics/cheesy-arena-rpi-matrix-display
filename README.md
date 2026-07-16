# Cheesy Arena RPi Matrix Display

Drives a 64x32 LED matrix panel from live [Cheesy Arena](https://github.com/Team254/cheesy-arena) FMS websocket data: team number, driver-station connection status, and full-screen E-Stop/Bypass overrides. See `plan.md` for the full project spec and `IMPLEMENTATION_PLAN.md` for the build plan.

## 🚀 Features
* **Direct WebSocket Connection:** Listens to the exact same live stream that the official FMS auxiliary displays use.
* **Priority Display Modes:** ESTOP > BYPASS > NORMAL (team # + connection dot) > IDLE, per `plan.md`'s override matrix.
* **Hardware-Free Development:** The render pipeline (`fms_client.py` → `state.py` → `renderer.py`) never touches hardware directly — `sinks.py` swaps between a `FileSink` (writes PNGs, any dev machine) and `MatrixSink` (real panel, Pi only).
* **Auto-Reconnect:** If the FMS server drops or reboots, the client automatically re-establishes the websocket handshake.
* **Headless Resiliency:** Runs as a systemd service (`systemd/cheesy-display.service`) that restarts on crash and on boot.

## 💻 Prerequisites

Dev machine (no hardware needed):
```bash
pip install -r requirements.txt
```

Raspberry Pi with the physical panel: follow `docs/PI_SETUP.md` in full — it covers OS setup, disabling onboard audio (GPIO conflict), and building the `rpi-rgb-led-matrix` Python bindings from source (not pip-installable).

## ⚙️ Configuration

Set via environment variables (see `config.py` for the full list and defaults), with `argparse` overrides for local runs:

```bash
python3 main.py --fms-ip 10.0.100.5 --station B1 --sink file
```

| Variable | Purpose | Default |
| --- | --- | --- |
| `CHEESY_FMS_IP` | Cheesy Arena server IP | `10.0.100.5` |
| `CHEESY_STATION` | Alliance station to monitor (e.g. `R1`, `B2`) | `B1` |
| `CHEESY_SINK` | `file` (dev/preview) or `matrix` (real panel) | `file` |
| `CHEESY_MATRIX_*` | Panel dimensions / hardware mapping / GPIO tuning | see `config.py` |

## ▶️ Usage

**No hardware, just proving the render pipeline works:**
```bash
python3 tools/preview.py   # writes out/*.png for all 5 fixture states
```

**On the Pi, driving the real panel:**
```bash
python3 main.py --sink matrix
```

**Hardware smoke test** (no FMS/websocket involved at all — just proves the Pi → HAT → panel chain works):
```bash
sudo python3 hardware_test.py
```

## 🧪 Tests
```bash
pip install pytest
pytest
```

## 🔮 Roadmap
* **FTA Diagnostic Boot Screen:** render the Pi's local IP on boot before connecting to the FMS, for easy SSH access without network scanning. Deferred — not part of core delivery (see `IMPLEMENTATION_PLAN.md`).
* Swap the IDLE-mode placeholder ("----") for the real Refinery logo once the asset is supplied (`assets/refinery_logo.png`).

## 📜 History
`fms_ws_test.py` is the original Phase 1 console prototype and is kept only as a historical reference — it's superseded by `main.py`. Its one bug (reading the connection-status key as `sConn` instead of `DsConn`) was carried forward into that file as-is, but was caught and fixed in `fms_client.py` (see `tests/test_fms_client.py::test_ds_conn_is_parsed_from_the_correct_key`).
