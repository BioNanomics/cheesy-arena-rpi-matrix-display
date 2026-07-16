# Implementation Plan: Cheesy Arena RPi Matrix Display

## Context

`plan.md` describes the full target system: a Raspberry Pi + Adafruit RGB Matrix HAT driving a 64x32 LED panel, showing live FMS data (team number, connection status, E-Stop/Bypass overrides) via a websocket connection to Cheesy Arena. The repo currently only has a Phase-1 console prototype (`fms_ws_test.py`) that prints parsed websocket data to the terminal — there is no rendering code and nothing has ever touched the physical LED matrix.

The immediate priority is getting anything visible on the physical panel — a hardware bring-up smoke test, independent of the websocket/FMS logic — before tackling the full FMS-driven display system.

This plan is split into two parts accordingly:
- **Part A** — a hardware bring-up checklist and standalone smoke-test script to prove the Pi → HAT → panel chain works.
- **Part B** — the follow-on architecture for the full FMS-driven display, to build after Part A succeeds.

---

## Part A: Hardware bring-up

Goal: Pi OS installed, `rpi-rgb-led-matrix` library built, and a trivial script proves the Pi → HAT → panel chain works, with zero dependency on Cheesy Arena or websockets.

### A1. `docs/PI_SETUP.md` — on-site runbook

A step-by-step doc to follow at the venue, covering:
1. **Flash Raspberry Pi OS Lite** (32-bit recommended for best compatibility with `rpi-rgb-led-matrix`) via Raspberry Pi Imager; enable SSH and configure Wi-Fi credentials in the imager's advanced options so the Pi is reachable headless for initial setup (Wi-Fi gets disabled later per `plan.md` §2, once the panel is confirmed working and the Pi moves to the field network).
2. **Disable onboard audio** — add `dtparam=audio=off` to `/boot/firmware/config.txt` (or blacklist `snd_bcm2835`). The onboard audio PWM conflicts with the GPIO pins the HAT uses for panel timing; skipping this causes visible flicker/glitches.
3. **Install build deps**: `sudo apt update && sudo apt install -y git build-essential python3-dev python3-pip python3-venv`.
4. **Clone and build the matrix library**:
   ```
   git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
   cd rpi-rgb-led-matrix
   make build-python PYTHON=$(which python3)
   sudo make install-python PYTHON=$(which python3)
   ```
5. **Create a venv that can see the system-installed `rgbmatrix` module**: `python3 -m venv --system-site-packages ~/cheesy-venv` (plain `venv` would hide the module `install-python` just placed in system site-packages).
6. **Clone this repo** onto the Pi, `source ~/cheesy-venv/bin/activate`, `pip install -r requirements.txt` (Part B; not needed for the smoke test itself, but fine to do now).
7. **Run the smoke test** (A2) with `sudo` (GPIO access requires root): `sudo ~/cheesy-venv/bin/python3 hardware_test.py`.
8. Troubleshooting notes: if nothing lights up, double check `--led-gpio-mapping`/`hardware_mapping` matches the actual board (`adafruit-hat` for the HAT/Bonnet per `plan.md` §2) and that the panel's ribbon cable orientation/power are correct.

### A2. `hardware_test.py` — standalone smoke test script

Lives at the repo root, has **zero dependency** on `websocket-client`, `fms_ws_test.py`, or any FMS logic — only `Pillow` and `rgbmatrix`. Purpose: prove the panel lights up correctly, and double as the first real exercise of the `Image → SetImage` path that Part B's renderer will reuse.

```python
from PIL import Image, ImageDraw, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions

options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.hardware_mapping = "adafruit-hat"
options.gpio_slowdown = 2

matrix = RGBMatrix(options=options)

image = Image.new("RGB", (64, 32), (0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rectangle((0, 0, 63, 31), outline=(0, 255, 0))
draw.text((4, 12), "HELLO", fill=(255, 255, 255))

matrix.SetImage(image)

try:
    input("Displaying test pattern. Press Enter to exit.\n")
finally:
    matrix.Clear()
```

Verification: run it on the Pi — panel should show a green border box with "HELLO" text in white. If colors/orientation look wrong, that's a `hardware_mapping`/wiring issue to resolve on the spot, not a code problem.

---

## Part B: Full FMS-driven display (follow-on, after Part A succeeds)

### Module structure
```
config.py       # Config dataclass + load_config() from env vars
fms_client.py    # WebSocketApp lifecycle, reconnect loop, JSON -> StationSnapshot (fixes the DsConn bug below)
state.py        # StationSnapshot, DisplayMode enum, compute_mode(), StateTracker (redraw-on-change)
renderer.py     # render_estop/bypass/normal/idle(snapshot) -> PIL.Image; render() dispatcher
sinks.py        # CanvasSink ABC; FileSink (dev, no hardware), MatrixSink (wraps rgbmatrix, deferred import)
main.py         # wires fms_client -> StateTracker -> renderer -> sink
assets/fonts/, assets/refinery_logo.png
systemd/cheesy-display.service
tools/preview.py   # replays fixture JSON through the pipeline into FileSink, no socket/hardware needed
tests/          # test_state.py, test_fms_client.py, test_renderer.py + fixtures/arena_status_samples.json
```

**Key design decision:** `renderer.py` only ever produces a `PIL.Image` (64x32) — it never touches `rgbmatrix` directly. `sinks.py` is the only place hardware is imported, and that import is deferred inside `MatrixSink.__init__`, so the whole pipeline (`fms_client`, `state`, `renderer`, `main.py --sink=file`) stays importable and testable on a dev machine with no Pi attached, using `hardware_test.py`'s same `Image → SetImage` call once `MatrixSink` is built.

### Fix the known bug
`fms_ws_test.py:34` reads `station_data.get("sConn")`, but `plan.md` §4's own example payload uses `"DsConn"`. When parsing moves into `fms_client.py`, correct this to `.get("DsConn")` and add a regression test built from `plan.md`'s own example JSON so this typo can't silently return.

### State machine (`state.py`)
Directly encodes `plan.md` §5's priority table:
```python
def compute_mode(s: StationSnapshot) -> DisplayMode:
    if s.estop: return DisplayMode.ESTOP
    if s.bypass: return DisplayMode.BYPASS
    if s.team_id is not None: return DisplayMode.NORMAL
    return DisplayMode.IDLE
```
`StateTracker` generalizes the prototype's `previous_state` string dedupe to gate `sink.show()` calls instead of `print()`.

### Rendering per mode
- ESTOP: `(220,20,20)` crimson bg, bold black "ESTOP" centered.
- BYPASS: `(255,191,0)` amber bg, bold black "BYPASS" centered.
- NORMAL: black bg; Zone 1 (x 0–48px) large white team number; Zone 2 (x 48–64px) green/red status dot for `ds_conn`.
- IDLE: black bg + `assets/refinery_logo.png` composited (RGBA alpha paste). **Logo asset doesn't exist yet** — placeholder text (e.g. "----") ships first with a `# TODO` marker until the real logo is supplied.
- Fonts: bundle a TTF under `assets/fonts/` (Pi OS Lite ships none by default) so dev-machine and Pi renders match exactly.

### Config (`config.py`)
Env vars as source of truth (`CHEESY_FMS_IP`, `CHEESY_STATION`, `CHEESY_SINK`, `CHEESY_MATRIX_*`), with `argparse` overrides in `main.py` for dev convenience. Matches systemd's `EnvironmentFile=` deployment model and keeps live-event IPs out of git.

### Deployment (`systemd/cheesy-display.service`)
`Restart=always`, `RestartSec=3`, `WantedBy=multi-user.target`, `EnvironmentFile=/etc/cheesy-display/config.env`, runs as root (GPIO/hardware-PWM access). Combined with `fms_client.py`'s own reconnect loop, this satisfies `plan.md` §6's "Headless Resiliency" requirement (survives both crashes and hard reboots).

### Delivery order
1. Refactor `fms_ws_test.py` → `fms_client.py` + `state.py` (fix `DsConn`), `main.py` still prints, but through the new module boundaries; add `test_state.py`/`test_fms_client.py`.
2. Build `renderer.py` + `sinks.py`, verify entirely off-hardware via `tools/preview.py` + `FileSink` against the 5 fixture states (estop/bypass/normal-connected/normal-disconnected/idle).
3. Swap in the real Refinery logo once supplied.
4. Build `MatrixSink`, run on the real Pi (reusing Part A's already-proven `rgbmatrix` setup) — smoke-test `MatrixSink` alone before wiring the full pipeline.
5. Add `config.py`, verify on dev machine (shell env vars) and Pi (`EnvironmentFile`).
6. Install the systemd unit; verify crash-restart (`kill -9`) and boot-start (reboot).

**Testing note:** Cheesy Arena (Team254/cheesy-arena) is open source and runnable locally in practice mode — pointing `CHEESY_FMS_IP` at `localhost` and manually toggling E-Stop/Bypass/team assignment in its UI gives full live end-to-end testing without the physical field network, if useful later.

**Explicitly deferred:** the "FTA Diagnostic Boot Screen" (`plan.md` §7) is future/optional — not part of core delivery.

---

## Verification

**Part A:** Run `sudo python3 hardware_test.py` on the Pi. Success = green border + "HELLO" text visible on the physical panel. Any garbled/wrong-color/no-output result is a `hardware_mapping`/wiring/library-build issue to debug on the spot using `docs/PI_SETUP.md`'s troubleshooting notes.

**Part B:** `tools/preview.py` against `tests/fixtures/arena_status_samples.json` produces correct PNGs for all 4 modes via `FileSink`; `pytest tests/` passes, including the `DsConn` regression test. Final on-hardware verification: run `main.py --sink=matrix` against a local Cheesy Arena instance (or the real field network) and confirm the panel updates live as match state changes.
