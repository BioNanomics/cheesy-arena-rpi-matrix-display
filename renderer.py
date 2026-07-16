"""Renders a StationSnapshot + DisplayMode into a PIL Image sized to match
the configured panel.

Never touches hardware directly -- output is always a plain PIL Image so
it can be exercised off-hardware via sinks.FileSink and pushed to the
panel via sinks.MatrixSink.
"""

import os

from PIL import Image, ImageDraw, ImageFont

from state import DisplayMode, StationSnapshot, team_number_text

# Defaults match the 64x32 panel plan.md targets; callers on a differently
# configured panel (config.py's CHEESY_MATRIX_ROWS/COLS) should pass their
# own width/height into render() so the image always matches the hardware
# MatrixSink was built with.
WIDTH = 64
HEIGHT = 32

TEAM_ZONE_FRACTION = 0.75  # Zone 1 (team number) as a fraction of total width

COLOR_ESTOP_BG = (220, 20, 20)
COLOR_BYPASS_BG = (255, 191, 0)
COLOR_TEXT_BLACK = (0, 0, 0)
COLOR_TEXT_WHITE = (255, 255, 255)
COLOR_BG_NORMAL = (0, 0, 0)
COLOR_CONNECTED = (0, 255, 0)
COLOR_DISCONNECTED = (255, 0, 0)

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
_FONT_PATH = os.path.join(_ASSETS_DIR, "fonts", "Silkscreen-Bold.ttf")
_LOGO_PATH = os.path.join(_ASSETS_DIR, "refinery_logo.png")

_font_alert = ImageFont.truetype(_FONT_PATH, 11)  # full-screen ESTOP/BYPASS text
_font_medium = ImageFont.truetype(_FONT_PATH, 9)

# Candidate sizes for the team number, largest first -- the largest one that
# fits the team zone's width is used, so a 5-digit team number shrinks
# instead of overflowing into the status-dot zone.
_team_font_sizes = [13, 12, 11, 10, 9]
_team_fonts = [ImageFont.truetype(_FONT_PATH, size) for size in _team_font_sizes]

_logo_image = Image.open(_LOGO_PATH).convert("RGBA") if os.path.exists(_LOGO_PATH) else None


def _new_canvas(bg_color, width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), bg_color)
    return image, ImageDraw.Draw(image)


def _draw_centered_text(draw: ImageDraw.ImageDraw, text: str, font, fill, box) -> None:
    x0, y0, x1, y1 = box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = x0 + ((x1 - x0) - text_w) / 2 - bbox[0]
    y = y0 + ((y1 - y0) - text_h) / 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


def _fit_team_font(draw: ImageDraw.ImageDraw, text: str, max_width: int):
    for font in _team_fonts:
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return _team_fonts[-1]  # smallest size, used as-is even if still too wide


def render_estop(_snapshot: StationSnapshot, width: int = WIDTH, height: int = HEIGHT) -> Image.Image:
    image, draw = _new_canvas(COLOR_ESTOP_BG, width, height)
    _draw_centered_text(draw, "ESTOP", _font_alert, COLOR_TEXT_BLACK, box=(0, 0, width, height))
    return image


def render_bypass(_snapshot: StationSnapshot, width: int = WIDTH, height: int = HEIGHT) -> Image.Image:
    image, draw = _new_canvas(COLOR_BYPASS_BG, width, height)
    _draw_centered_text(draw, "BYPASS", _font_alert, COLOR_TEXT_BLACK, box=(0, 0, width, height))
    return image


def render_normal(snapshot: StationSnapshot, width: int = WIDTH, height: int = HEIGHT) -> Image.Image:
    image, draw = _new_canvas(COLOR_BG_NORMAL, width, height)

    team_zone_width = int(width * TEAM_ZONE_FRACTION)
    status_zone_width = width - team_zone_width

    team_number = team_number_text(snapshot)
    margin = 2
    font = _fit_team_font(draw, team_number, team_zone_width - margin)
    _draw_centered_text(draw, team_number, font, COLOR_TEXT_WHITE, box=(0, 0, team_zone_width, height))

    dot_color = COLOR_CONNECTED if snapshot.ds_conn else COLOR_DISCONNECTED
    dot_radius = min(6, status_zone_width // 2, height // 2)
    cx = team_zone_width + status_zone_width / 2
    cy = height / 2
    draw.ellipse(
        (cx - dot_radius, cy - dot_radius, cx + dot_radius, cy + dot_radius),
        fill=dot_color,
    )

    return image


def render_idle(_snapshot: StationSnapshot, width: int = WIDTH, height: int = HEIGHT) -> Image.Image:
    image, draw = _new_canvas(COLOR_BG_NORMAL, width, height)

    if _logo_image is not None:
        x = (width - _logo_image.width) // 2
        y = (height - _logo_image.height) // 2
        image.paste(_logo_image, (x, y), _logo_image)
    else:
        # TODO: swap in the real Refinery logo once supplied (assets/refinery_logo.png).
        _draw_centered_text(draw, "----", _font_medium, COLOR_TEXT_WHITE, box=(0, 0, width, height))

    return image


_RENDERERS = {
    DisplayMode.ESTOP: render_estop,
    DisplayMode.BYPASS: render_bypass,
    DisplayMode.NORMAL: render_normal,
    DisplayMode.IDLE: render_idle,
}


def render(mode: DisplayMode, snapshot: StationSnapshot, width: int = WIDTH, height: int = HEIGHT) -> Image.Image:
    return _RENDERERS[mode](snapshot, width, height)
