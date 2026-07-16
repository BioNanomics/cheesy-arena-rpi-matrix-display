"""Output targets for a rendered frame.

MatrixSink defers its rgbmatrix import until construction so that
fms_client/state/renderer/main.py stay importable (and testable) on a
machine with no Pi hardware attached.
"""

from abc import ABC, abstractmethod

from PIL import Image


class CanvasSink(ABC):
    @abstractmethod
    def show(self, image: Image.Image) -> None: ...

    def close(self) -> None:
        pass


class FileSink(CanvasSink):
    """Writes each frame to a PNG on disk. For dev-machine use, no hardware required."""

    def __init__(self, path: str = "preview.png") -> None:
        self.path = path

    def show(self, image: Image.Image) -> None:
        image.save(self.path)


class MatrixSink(CanvasSink):
    """Pushes each frame to a physical LED panel via rpi-rgb-led-matrix."""

    def __init__(self, config) -> None:
        from rgbmatrix import RGBMatrix, RGBMatrixOptions

        options = RGBMatrixOptions()
        options.rows = config.matrix_rows
        options.cols = config.matrix_cols
        options.hardware_mapping = config.matrix_hardware_mapping
        options.gpio_slowdown = config.matrix_gpio_slowdown
        options.brightness = config.matrix_brightness
        options.pwm_bits = config.matrix_pwm_bits

        self._matrix = RGBMatrix(options=options)

    def show(self, image: Image.Image) -> None:
        self._matrix.SetImage(image.convert("RGB"))

    def close(self) -> None:
        self._matrix.Clear()


def build_sink(config) -> CanvasSink:
    if config.sink_type == "matrix":
        return MatrixSink(config)
    if config.sink_type == "file":
        return FileSink()
    raise ValueError(f"Unknown sink type: {config.sink_type}")
