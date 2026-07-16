"""Entry point: connects to the FMS and drives the display pipeline."""

from config import load_config
from fms_client import run_forever
from renderer import render
from sinks import build_sink
from state import DisplayMode, StateTracker, StationSnapshot, team_number_text


def status_text(mode: DisplayMode, snapshot: StationSnapshot) -> str:
    if mode is DisplayMode.ESTOP:
        return "!!! ESTOPPED !!!"
    if mode is DisplayMode.BYPASS:
        return "BYPASSED"
    if mode is DisplayMode.NORMAL:
        return "CONNECTED [O]" if snapshot.ds_conn else "DISCONNECTED [X]"
    return "IDLE"


def make_handler(tracker, sink, width, height):
    def handle_snapshot(snapshot: StationSnapshot) -> None:
        changed, mode = tracker.should_redraw(snapshot)
        if not changed:
            return

        team_number = team_number_text(snapshot)
        if snapshot.team_id is None:
            team_name = "Empty Station"
        else:
            team_name = snapshot.team_nickname or "Unknown"

        print("\n--- FMS UPDATE ---")
        print(f"Mode:    {mode.name}")
        print(f"Team:    {team_number} ({team_name})")
        print(f"Status:  {status_text(mode, snapshot)}")
        print("-" * 18)

        sink.show(render(mode, snapshot, width=width, height=height))

    return handle_snapshot


if __name__ == "__main__":
    config = load_config()
    sink = build_sink(config)
    tracker = StateTracker()

    handler = make_handler(tracker, sink, width=config.matrix_cols, height=config.matrix_rows)
    try:
        run_forever(config.fms_ip, config.target_station, handler)
    finally:
        sink.close()
