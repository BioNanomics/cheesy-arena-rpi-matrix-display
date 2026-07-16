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

BORDER_THICKNESS = 2  # connection-status indicator: a border around the whole panel

COLOR_ESTOP_BG = (220, 20, 20)
COLOR_BYPASS_BG = (255, 90, 0)
COLOR_TEXT_BLACK = (0, 0, 0)
COLOR_TEXT_WHITE = (255, 255, 255)
COLOR_BG_NORMAL = (0, 0, 0)
COLOR_CONNECTED = (0, 255, 0)
COLOR_DISCONNECTED = (255, 0, 0)
COLOR_ALLIANCE_RED = (255, 40, 40)
COLOR_ALLIANCE_BLUE = (40, 120, 255)

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
_FONT_PATH = os.path.join(_ASSETS_DIR, "fonts", "PressStart2P-Regular.ttf")
_LOGO_PATH = os.path.join(_ASSETS_DIR, "refinery_logo.png")

_font_alert = ImageFont.truetype(_FONT_PATH, 9)  # full-screen ESTOP/BYPASS text
_font_medium = ImageFont.truetype(_FONT_PATH, 9)

# Candidate sizes for the team number, largest first -- the largest one that
# fits the available space is used, so a 5-digit team number shrinks instead
# of overflowing into the border. Press Start 2P is roughly monospace/square
# per character, so size scales fairly evenly with available width.
_team_font_sizes = list(range(32, 5, -1))
_team_fonts = [ImageFont.truetype(_FONT_PATH, size) for size in _team_font_sizes]

_logo_image = Image.open(_LOGO_PATH).convert("RGBA") if os.path.exists(_LOGO_PATH) else None


def _new_canvas(bg_color, width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    return image, draw


def _draw_centered_text(draw: ImageDraw.ImageDraw, image: Image.Image, text: str, font, fill, box) -> None:
    x0, y0, x1, y1 = box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = x0 + ((x1 - x0) - text_w) / 2 - bbox[0]
    y = y0 + ((y1 - y0) - text_h) / 2 - bbox[1]

    # Render at default AA quality (correct hinting/shape -- FreeType's mono
    # rasterizer distorts thin features like the "4"'s diagonal gap, closing
    # it into something that reads as "9") into a mask, then threshold the
    # mask ourselves so the final pixels are still fully on/off on the panel,
    # with no blended anti-aliased fringe color.
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).text((x, y), text, font=font, fill=255)
    mask = mask.point(lambda v: 255 if v >= 128 else 0)
    image.paste(fill, (0, 0), mask)


def _fit_team_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_height: int = HEIGHT):
    for font in _team_fonts:
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width and bbox[3] - bbox[1] <= max_height:
            return font
    return _team_fonts[-1]  # smallest size, used as-is even if still too wide


def render_estop(_snapshot: StationSnapshot, width: int = WIDTH, height: int = HEIGHT) -> Image.Image:
    image, draw = _new_canvas(COLOR_ESTOP_BG, width, height)
    _draw_centered_text(draw, image, "ESTOP", _font_alert, COLOR_TEXT_BLACK, box=(0, 0, width, height))
    return image


def render_bypass(_snapshot: StationSnapshot, width: int = WIDTH, height: int = HEIGHT) -> Image.Image:
    image, draw = _new_canvas(COLOR_BYPASS_BG, width, height)
    _draw_centered_text(draw, image, "BYPASS", _font_alert, COLOR_TEXT_BLACK, box=(0, 0, width, height))
    return image


def render_normal(snapshot: StationSnapshot, width: int = WIDTH, height: int = HEIGHT) -> Image.Image:
    image, draw = _new_canvas(COLOR_BG_NORMAL, width, height)

    border_color = COLOR_CONNECTED if snapshot.ds_conn else COLOR_DISCONNECTED
    draw.rectangle((0, 0, width - 1, height - 1), outline=border_color, width=BORDER_THICKNESS)

    team_number = team_number_text(snapshot)
    margin = BORDER_THICKNESS + 1  # keep the number clear of the border itself
    font = _fit_team_font(draw, team_number, width - 2 * margin, height - 2 * margin)
    team_color = COLOR_ALLIANCE_RED if snapshot.alliance == "red" else COLOR_ALLIANCE_BLUE
    _draw_centered_text(draw, image, team_number, font, team_color, box=(0, 0, width, height))

    return image


def render_idle(_snapshot: StationSnapshot, width: int = WIDTH, height: int = HEIGHT) -> Image.Image:
    image, draw = _new_canvas(COLOR_BG_NORMAL, width, height)

    if _logo_image is not None:
        x = (width - _logo_image.width) // 2
        y = (height - _logo_image.height) // 2
        image.paste(_logo_image, (x, y), _logo_image)
    else:
        # Fallback if assets/refinery_logo.png is ever missing (e.g. a checkout that didn't pull it).
        _draw_centered_text(draw, image, "----", _font_medium, COLOR_TEXT_WHITE, box=(0, 0, width, height))

    return image


_RENDERERS = {
    DisplayMode.ESTOP: render_estop,
    DisplayMode.BYPASS: render_bypass,
    DisplayMode.NORMAL: render_normal,
    DisplayMode.IDLE: render_idle,
}


def render(mode: DisplayMode, snapshot: StationSnapshot, width: int = WIDTH, height: int = HEIGHT) -> Image.Image:
    return _RENDERERS[mode](snapshot, width, height)
