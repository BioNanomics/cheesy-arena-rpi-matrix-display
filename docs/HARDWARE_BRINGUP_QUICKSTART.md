# Hardware Bring-Up Quickstart (OS already flashed)

Path from a Pi that already has Raspberry Pi OS Lite installed, plus the
files on the USB drive (`hardware_test.py`, `PI_SETUP.md`,
`requirements.txt`), to a working smoke test on the physical panel.

For the full runbook including OS flashing from scratch, see `PI_SETUP.md`.

## 0. Physically assemble (if not done)

Seat the Adafruit RGB Matrix HAT onto the Pi's GPIO header, connect the
panel via its ribbon cable, and connect the panel's separate power supply
(the HAT doesn't power the panel off the Pi's USB power alone). Double
check ribbon cable orientation — reversed cables are the #1 cause of
"nothing lights up."

## 1. Get on the Pi

Console (keyboard+monitor) or SSH if already enabled in the imager:

```bash
ssh <username>@<pi-ip-or-hostname>.local
```

If SSH wasn't enabled during flashing, you'll need a keyboard/monitor for
this first login, or re-flash with SSH enabled — no way around that
headlessly.

## 2. Disable onboard audio

The audio PWM conflicts with the GPIO pins the HAT uses for panel timing —
skip this and you'll get flicker/glitches.

```bash
sudo nano /boot/firmware/config.txt
```

Add the line:

```
dtparam=audio=off
```

Save, then:

```bash
sudo reboot
```

## 3. Install build dependencies

After reboot, SSH back in:

```bash
sudo apt update && sudo apt install -y git build-essential python3-dev python3-pip python3-venv cython3 python3-pil
```

## 4. Clone the matrix library

```bash
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix
```

(Don't build yet — the venv needs to exist first, see next step.)

## 5. Create a venv and install the Python bindings into it

As of Feb 2026 the project switched from `make build-python` /
`make install-python` to a `pip install .` build (cmake +
scikit-build-core under the hood), so a plain venv is all you need now —
no `--system-site-packages` required:

```bash
python3 -m venv ~/cheesy-venv
source ~/cheesy-venv/bin/activate
pip install .
cd ~
```

**Needs internet access** — `pip install .` downloads `cmake` and
`scikit-build-core` from PyPI to compile the extension. Do this *before*
disabling Wi-Fi for the field network.

## 6. Get the USB drive's files onto the Pi

Plug the USB stick directly into the Pi (easiest option since it's FAT16,
natively readable by Linux):

```bash
lsblk                          # find the device, e.g. /dev/sda1
sudo mkdir -p /mnt/usb
sudo mount /dev/sda1 /mnt/usb
mkdir -p ~/cheesy-hardware-test
cp /mnt/usb/cheesy-hardware-test/* ~/cheesy-hardware-test/
sudo umount /mnt/usb
cd ~/cheesy-hardware-test
```

## 7. Install this project's Python deps

Still inside the activated venv:

```bash
pip install -r requirements.txt
```

## 8. Run the smoke test

GPIO access needs root, so use `sudo` with the venv's own Python directly:

```bash
sudo ~/cheesy-venv/bin/python3 hardware_test.py
```

**Success** = a green border box with white "HELLO" text on the panel.
It'll wait for Enter to exit and clear the display.

## If it doesn't work

- **Nothing lights up**: check panel power and ribbon cable
  orientation first — usually physical, not code.
- **Wrong colors / garbled / mirrored**: `hardware_mapping =
  "adafruit-hat"` in `hardware_test.py` should already be correct for
  both the HAT and Bonnet variants — if it's still wrong, you may be on a
  different driver board.
- **Flickering**: confirm step 2 actually took effect
  (`cat /boot/firmware/config.txt | grep audio` should show
  `dtparam=audio=off`) and that you rebooted after.
- **`ImportError: No module named rgbmatrix`**: step 5's `pip install .`
  didn't complete, or you're running a different Python than the one the
  venv you activated (double-check `which python3` and `which pip` point
  into `~/cheesy-venv`).
- **`make: *** No rule to make target 'build-python'. Stop.`**: you're
  following outdated instructions (the old `make build-python` /
  `make install-python` method). The project switched to `pip install .`
  in Feb 2026 — use step 5 above instead.
- **`fatal error: Imaging.h: No such file or directory`** while building
  `pillow.c`: missing the `python3-pil` apt package (it ships Pillow's C
  headers; the pip-installed `Pillow` wheel does not). Run
  `sudo apt-get install -y python3-pil` and retry `pip install .`.

Once this works, the next step is wiring up the full FMS pipeline
(`main.py --sink matrix`) instead of just the smoke test.
