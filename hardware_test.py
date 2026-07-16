"""Standalone LED matrix smoke test.

Proves the Pi -> HAT -> panel chain works before any FMS/websocket code
is involved. Run with sudo (GPIO access requires root):

    sudo python3 hardware_test.py

Requires Pillow and the rgbmatrix bindings built per docs/PI_SETUP.md.
"""

from PIL import Image, ImageDraw
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
