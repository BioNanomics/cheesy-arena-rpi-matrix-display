"""Configuration loading: environment variables as the source of truth."""

import argparse
import os
from dataclasses import dataclass


_TRUTHY = {"1", "true", "yes", "on"}


@dataclass
class Config:
    fms_ip: str
    target_station: str
    sink_type: str = "file"
    matrix_rows: int = 32
    matrix_cols: int = 64
    matrix_hardware_mapping: str = "adafruit-hat"
    matrix_gpio_slowdown: int = 2
    matrix_brightness: int = 100
    matrix_pwm_bits: int = 11
    basic_mode: bool = False


def load_config() -> Config:
    """Load config from environment variables, with argparse overrides for dev convenience."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--fms-ip")
    parser.add_argument("--station")
    parser.add_argument("--sink", choices=["file", "matrix"])
    parser.add_argument("--basic-mode", action="store_true", default=None)
    args, _unknown = parser.parse_known_args()

    if args.basic_mode is not None:
        basic_mode = args.basic_mode
    else:
        basic_mode = os.environ.get("CHEESY_BASIC_MODE", "false").strip().lower() in _TRUTHY

    return Config(
        fms_ip=args.fms_ip or os.environ.get("CHEESY_FMS_IP", "10.0.100.5"),
        target_station=args.station or os.environ.get("CHEESY_STATION", "B1"),
        sink_type=args.sink or os.environ.get("CHEESY_SINK", "file"),
        matrix_rows=int(os.environ.get("CHEESY_MATRIX_ROWS", 32)),
        matrix_cols=int(os.environ.get("CHEESY_MATRIX_COLS", 64)),
        matrix_hardware_mapping=os.environ.get("CHEESY_MATRIX_HARDWARE_MAPPING", "adafruit-hat"),
        matrix_gpio_slowdown=int(os.environ.get("CHEESY_MATRIX_GPIO_SLOWDOWN", 2)),
        matrix_brightness=int(os.environ.get("CHEESY_MATRIX_BRIGHTNESS", 100)),
        matrix_pwm_bits=int(os.environ.get("CHEESY_MATRIX_PWM_BITS", 11)),
        basic_mode=basic_mode,
    )
