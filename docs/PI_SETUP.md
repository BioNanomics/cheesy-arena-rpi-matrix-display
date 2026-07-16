# Raspberry Pi Hardware Bring-Up Runbook

Step-by-step setup to get from a blank SD card to a working LED matrix smoke
test (`hardware_test.py`). Follow in order; each step is a prerequisite for
the next.

## 1. Flash the OS

Use Raspberry Pi Imager to flash **Raspberry Pi OS Lite (32-bit)** — 32-bit
is recommended for best compatibility with `rpi-rgb-led-matrix`. In the
imager's advanced options (gear icon):

- Enable SSH.
- Set a hostname/username/password.
- Configure Wi-Fi credentials so the Pi is reachable headless for setup.

Wi-Fi is only for initial setup convenience. Per the project plan, Wi-Fi
gets disabled once the panel is confirmed working and the Pi is moved onto
the field network (hardwired only during live events).

## 2. Disable onboard audio

The onboard audio PWM conflicts with the GPIO pins the HAT uses for panel
timing. Skipping this causes visible flicker/glitches on the display.

Edit `/boot/firmware/config.txt` and add:

```
dtparam=audio=off
```

Reboot after saving.

## 3. Install build dependencies

```bash
sudo apt update
sudo apt install -y git build-essential python3-dev python3-pip python3-venv cython3 python3-pil
```

## 4. Clone the matrix library

```bash
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix
```

Don't build yet — create the venv first (next step), since the bindings
now install directly into it.

## 5. Create a venv and install the Python bindings

As of Feb 2026 the project switched from `make build-python` /
`make install-python` to a `pip install .` build (cmake + scikit-build-core
under the hood), so a plain venv works fine now — no
`--system-site-packages` needed:

```bash
python3 -m venv ~/cheesy-venv
source ~/cheesy-venv/bin/activate
pip install .
cd ~
```

This step needs internet access — `pip install .` pulls `cmake` and
`scikit-build-core` from PyPI to compile the extension. Do it before
disabling Wi-Fi for the field network (step 1's Wi-Fi is only for initial
setup and gets turned off later).

## 6. Clone this repo and install Python deps

```bash
git clone <this-repo-url> ~/cheesy-arena-rpi-matrix-display
cd ~/cheesy-arena-rpi-matrix-display
pip install -r requirements.txt
```

(`requirements.txt` covers the websocket/FMS side of the project — not
required for the smoke test itself, but fine to do now.)

## 7. Run the smoke test

GPIO access requires root, so run with `sudo` using the venv's Python
directly:

```bash
sudo ~/cheesy-venv/bin/python3 hardware_test.py
```

Expected result: a green border box with white "HELLO" text on the panel.

## 8. Deploy as a systemd service (headless resiliency)

Once the smoke test passes and the full FMS-driven pipeline (`main.py`) is
ready to run unattended:

```bash
sudo mkdir -p /etc/cheesy-display
sudo cp systemd/config.env.example /etc/cheesy-display/config.env
sudo nano /etc/cheesy-display/config.env   # set the real FMS IP / station

sudo mkdir -p /opt/cheesy-arena-rpi-matrix-display
sudo cp -r . /opt/cheesy-arena-rpi-matrix-display
sudo cp -r ~/cheesy-venv /opt/cheesy-arena-rpi-matrix-display/venv

sudo cp systemd/cheesy-display.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cheesy-display
```

Verify: `sudo systemctl status cheesy-display` and `journalctl -u cheesy-display -f`.
`Restart=always` recovers from crashes; `WantedBy=multi-user.target` +
`systemctl enable` recovers from a hard reboot; `fms_client.py`'s own
reconnect loop recovers from FMS server restarts/network blips.

## Troubleshooting

- **Nothing lights up at all**: check panel power and the ribbon cable
  connection/orientation first — most "no output" issues are physical, not
  code.
- **Wrong colors / garbled output / mirrored image**: `hardware_mapping` in
  `hardware_test.py` (`"adafruit-hat"`) must match the actual board. If
  you're using the plain Adafruit RGB Matrix Bonnet rather than the HAT,
  this value is still `adafruit-hat` (both use the same mapping); double
  check you're not on a different HAT/driver board that needs a different
  value.
- **Flickering**: confirm step 2 (onboard audio disabled) was applied and
  the Pi was rebooted afterward.
- **`ImportError: No module named rgbmatrix`**: step 5's `pip install .`
  didn't complete, or you're not running the Python from `~/cheesy-venv`
  (check `which python3`/`which pip`) — re-check step 5.
- **`make: *** No rule to make target 'build-python'. Stop.`**: you're
  following outdated instructions (the old `make build-python` /
  `make install-python` method). The project switched to `pip install .`
  in Feb 2026 — use step 5 above instead.
- **`fatal error: Imaging.h: No such file or directory`** while building
  `pillow.c`: missing the `python3-pil` apt package (it ships Pillow's C
  headers; the pip-installed `Pillow` wheel does not). Run
  `sudo apt-get install -y python3-pil` and retry `pip install .`.
