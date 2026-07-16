from PIL import Image, ImageDraw

from renderer import HEIGHT, WIDTH, _fit_team_font, render
from state import DisplayMode, StationSnapshot


def snapshot(**overrides):
    defaults = dict(team_id=9431, team_nickname="Refinery", ds_conn=True, estop=False, bypass=False)
    defaults.update(overrides)
    return StationSnapshot(**defaults)


def test_all_modes_render_correct_size():
    for mode in DisplayMode:
        image = render(mode, snapshot())
        assert isinstance(image, Image.Image)
        assert image.size == (WIDTH, HEIGHT)


def test_estop_background_is_crimson():
    image = render(DisplayMode.ESTOP, snapshot())
    assert image.getpixel((0, 0)) == (220, 20, 20)


def test_bypass_background_is_amber():
    image = render(DisplayMode.BYPASS, snapshot())
    assert image.getpixel((0, 0)) == (255, 191, 0)


def test_normal_status_dot_reflects_connection():
    connected = render(DisplayMode.NORMAL, snapshot(ds_conn=True))
    disconnected = render(DisplayMode.NORMAL, snapshot(ds_conn=False))

    dot_pixel = (60, 16)  # inside the status gutter (zone 2)
    assert connected.getpixel(dot_pixel) == (0, 255, 0)
    assert disconnected.getpixel(dot_pixel) == (255, 0, 0)


def test_idle_renders_without_crashing():
    image = render(DisplayMode.IDLE, snapshot(team_id=None, team_nickname=None))
    assert image.size == (WIDTH, HEIGHT)


def test_render_honors_custom_dimensions():
    # Regression test: renderer.WIDTH/HEIGHT used to be hardcoded, decoupled
    # from config.py's configurable matrix_rows/matrix_cols, which could
    # push a 64x32 image into a differently-sized MatrixSink.
    image = render(DisplayMode.NORMAL, snapshot(), width=32, height=16)
    assert image.size == (32, 16)


def test_team_font_shrinks_to_fit_wide_team_numbers():
    # Regression test: a 5-digit team number used to overflow the 48px team
    # zone (measured at 55px wide at the fixed font size) and collide with
    # the status dot. The font must now shrink to fit instead.
    draw = ImageDraw.Draw(Image.new("RGB", (WIDTH, HEIGHT)))
    max_width = 46
    font = _fit_team_font(draw, "99999", max_width)
    bbox = draw.textbbox((0, 0), "99999", font=font)
    assert bbox[2] - bbox[0] <= max_width


def test_five_digit_team_number_does_not_overlap_status_dot():
    image = render(DisplayMode.NORMAL, snapshot(team_id=99999, ds_conn=True))
    dot_pixel = (60, 16)
    assert image.getpixel(dot_pixel) == (0, 255, 0)
