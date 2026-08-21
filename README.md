# cheesy-arena-rpi-matrix-display

A Raspberry Pi + RGB LED matrix panel that shows live alliance-station status
from a [Cheesy Arena](https://github.com/Team254/cheesy-arena) FMS — team
number, driver-station connection, E-Stop, and Bypass — on a physical
64x32 panel at the venue.

```
        ┌────────────────────────────────┐
        │ ████████████████████████████   │  green/red border = DS connected/not
        │ █                          █   │
        │ █          2 9 1 0         █   │  alliance-colored team number
        │ █                          █   │  (7-segment style digits)
        │ █                          █   │
        │ ████████████████████████████   │
        └────────────────────────────────┘
```

No team assigned → shows a logo instead. E-Stopped or Bypassed → the whole
panel flashes to a solid alert screen. All of this can also be stripped down
to just the number/logo ("basic mode"), switchable live from Cheesy Arena's
own admin UI — see [Basic mode](#basic-mode-live-toggle) below.

## How it works

```
Cheesy Arena FMS ──(websocket)──> fms_client.py ──> state.py ──> renderer.py ──> sinks.py ──> panel
```

1. **`fms_client.py`** opens a websocket to Cheesy Arena's
   `/displays/alliance_station/websocket` endpoint and reconnects
   automatically if the connection drops or the FMS restarts. It parses two
   message types: `arenaStatus` (team/connection/E-Stop/Bypass data) and
   `displayConfiguration` (a live config push — see Basic mode below).
2. **`state.py`** turns the raw station fields into a `StationSnapshot` and
   decides the display mode from a fixed priority order: **E-Stop > Bypass >
   Team Assigned > Idle**. `StateTracker` only triggers a redraw when
   something actually changed, so the panel isn't repainting on every
   websocket tick.
3. **`renderer.py`** draws a `StationSnapshot` + mode into a plain PIL
   `Image` — it never touches hardware directly, which is what makes it
   testable on a laptop with no Pi attached.
4. **`sinks.py`** pushes that image either to a real LED panel
   (`MatrixSink`, via `rpi-rgb-led-matrix`) or to a PNG on disk (`FileSink`,
   for dev-machine iteration).
5. **`main.py`** wires all of the above together, and shows the idle/logo
   screen immediately on startup — before the FMS connection is even
   attempted — so the panel isn't dark while waiting for Cheesy Arena to
   come up or become reachable.

## Hardware

- Raspberry Pi (any model the [Adafruit RGB Matrix
  HAT/Bonnet](https://www.adafruit.com/product/2345) supports)
- Adafruit RGB Matrix HAT or Bonnet (both use the same `adafruit-hat`
  driver mapping)
- A 64x32 RGB LED matrix panel with its own power supply (the HAT does not
  power the panel off the Pi's USB power alone)

For first-time hardware bring-up from a blank SD card — flashing the OS,
disabling onboard audio (required, or the panel flickers), building
`rpi-rgb-led-matrix`, and running the `hardware_test.py` smoke test — see
[`docs/PI_SETUP.md`](docs/PI_SETUP.md). If the OS is already flashed and you
just need to get from there to a working smoke test, see
[`docs/HARDWARE_BRINGUP_QUICKSTART.md`](docs/HARDWARE_BRINGUP_QUICKSTART.md).

## Running it

Requires the `rgbmatrix` Python bindings (built per the docs above) for
real hardware output, or nothing extra to run against a `FileSink` for
dev-machine testing.

```bash
pip install -r requirements.txt

# Against real hardware (needs root for GPIO access):
sudo ~/cheesy-venv/bin/python3 main.py --sink matrix --fms-ip 10.0.100.5 --station B1

# Dev machine, no panel attached -- writes each frame to preview.png:
python3 main.py --sink file --fms-ip 10.0.100.5 --station B1
```

`--station` is the alliance station this Pi represents, e.g. `R1`, `R2`,
`R3`, `B1`, `B2`, `B3` — it determines both which station's data this
display shows and its alliance color (red/blue).

## Configuration

Everything is a `CHEESY_*` environment variable (`config.py`), with CLI
flags available for local overrides:

| Env var | CLI flag | Default | Meaning |
|---|---|---|---|
| `CHEESY_FMS_IP` | `--fms-ip` | `10.0.100.5` | Cheesy Arena server address |
| `CHEESY_STATION` | `--station` | `B1` | Alliance station this display represents |
| `CHEESY_SINK` | `--sink` | `file` | `matrix` (real panel) or `file` (writes `preview.png`) |
| `CHEESY_MATRIX_ROWS` | — | `32` | Panel rows |
| `CHEESY_MATRIX_COLS` | — | `64` | Panel columns |
| `CHEESY_MATRIX_HARDWARE_MAPPING` | — | `adafruit-hat` | rpi-rgb-led-matrix driver mapping |
| `CHEESY_MATRIX_GPIO_SLOWDOWN` | — | `2` | Raise if you see ghosting/flicker on Pi 4 |
| `CHEESY_MATRIX_BRIGHTNESS` | — | `100` | Panel brightness (0-100) |
| `CHEESY_MATRIX_PWM_BITS` | — | `11` | Color-depth timing tradeoff |
| `CHEESY_BASIC_MODE` | `--basic-mode` | `false` | Startup default for basic mode (see below) |

For a live deployment, copy `systemd/config.env.example` to
`/etc/cheesy-display/config.env` and fill in the real FMS IP/station.

## Basic mode (live toggle)

Basic mode strips the display down to just the alliance-colored team number
(or the logo, when idle) — no connection-status border, no idle accent
bars, and E-Stop/Bypass are suppressed back to the normal number display.
Useful when you just want a plain team sign rather than a full status
readout.

It's switchable **live, while the display is running, with no SSH and no
restart** — Cheesy Arena already has a per-display "Configuration" field
that this project uses instead of needing its own separate tool. On Cheesy
Arena's **Setup → Displays** page, find this display's row and set its
Configuration box to:

```
mode=basic
```

Save, and the panel updates within moments. To go back to full-featured
mode, clear the box (or set `mode=full` — anything other than exactly
`basic` works, but `mode=full` is clearest for whoever edits it next).

`CHEESY_BASIC_MODE` in `config.env` only controls the *startup* default —
what the display shows before anyone has touched its Configuration box —
since the whole point of this mechanism is that it's changeable live from
Cheesy Arena afterward.

## Deploying as a systemd service

So the display survives reboots and FMS restarts unattended:

```bash
sudo mkdir -p /etc/cheesy-display
sudo cp systemd/config.env.example /etc/cheesy-display/config.env
sudo nano /etc/cheesy-display/config.env   # set the real FMS IP / station

sudo cp systemd/cheesy-display.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cheesy-display
```

`systemd/cheesy-display.service` expects the repo at
`/home/admin/cheesy-arena-rpi-matrix-display` and the venv at
`/home/admin/cheesy-venv` — adjust both the service file and the paths
above if your Pi's username/layout differs.

Check on it with:

```bash
sudo systemctl status cheesy-display
sudo journalctl -u cheesy-display -f
```

`Restart=always` recovers from crashes, `WantedBy=multi-user.target` +
`systemctl enable` recovers from a hard reboot, and `fms_client.py`'s own
reconnect loop recovers from FMS restarts or network blips — between the
three, and the panel showing its idle logo immediately on boot, the
display should never need to be touched once it's deployed.

## Project layout

```
main.py              Entry point -- wires fms_client -> state -> renderer -> sinks together
config.py             CHEESY_* env var / CLI flag loading
fms_client.py          Websocket connection, reconnect loop, message parsing
state.py               StationSnapshot, display-mode priority logic, redraw-on-change tracking
renderer.py             StationSnapshot + mode -> PIL Image (hardware-agnostic, unit-testable)
sinks.py                 PIL Image -> real LED panel (MatrixSink) or PNG file (FileSink)
hardware_test.py        Standalone smoke test -- proves Pi/HAT/panel wiring before any FMS code runs
assets/                  Logo + fonts (DSEG7 for team numbers, Pixelify Sans for status text)
systemd/                 Service unit + example env file for unattended deployment
docs/PI_SETUP.md          Full hardware bring-up runbook, blank SD card to working panel
docs/HARDWARE_BRINGUP_QUICKSTART.md   Same, but for a Pi that already has the OS flashed
```

## Rendering notes

- Team numbers use **DSEG7 Modern Bold**, a 7-segment "digital scoreboard"
  font — chosen because it's built from a handful of simple geometric
  segments per digit, so it stays crisp and unambiguous at small sizes with
  none of the corrupted/crowded-glyph issues that came up with several
  pixel-art fonts during development.
- All text is rendered anti-aliased into a mask and then thresholded to
  pure on/off pixels before being pasted onto the panel — this keeps
  FreeType's hinting/shape correct while still avoiding any blended
  anti-aliased fringe color on the actual LEDs.
- ESTOP/BYPASS background colors and the idle-screen accent bars are
  deliberately dimmed (75% and 40% brightness respectively) so they don't
  overpower the rest of the display.
