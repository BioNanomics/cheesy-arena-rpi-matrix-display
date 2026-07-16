"""Replays the fixture arenaStatus payloads through the full pipeline
(parse -> compute_mode -> render) and writes one PNG per mode to out/.

No websocket connection or hardware required:

    python3 tools/preview.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fms_client import parse_station_snapshot
from renderer import render
from state import compute_mode

FIXTURES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "tests", "fixtures", "arena_status_samples.json"
)
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "out")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(FIXTURES_PATH) as f:
        fixtures = json.load(f)

    for name, payload in fixtures.items():
        snapshot = parse_station_snapshot(json.dumps(payload), "B1")
        mode = compute_mode(snapshot)
        image = render(mode, snapshot)

        out_path = os.path.join(OUT_DIR, f"{name}.png")
        image.save(out_path)
        print(f"{name:20s} -> {mode.name:8s} -> {out_path}")


if __name__ == "__main__":
    main()
