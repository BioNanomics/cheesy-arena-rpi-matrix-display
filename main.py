"""Entry point: connects to the FMS and drives the display pipeline."""

from config import load_config
from fms_client import run_forever
from renderer import render
from sinks import build_sink
from state import DisplayMode, StateTracker, StationSnapshot, compute_mode, team_number_text


def status_text(mode: DisplayMode, snapshot: StationSnapshot) -> str:
    if mode is DisplayMode.ESTOP:
        return "!!! ESTOPPED !!!"
    if mode is DisplayMode.BYPASS:
        return "BYPASSED"
    if mode is DisplayMode.NORMAL:
        return "CONNECTED [O]" if snapshot.ds_conn else "DISCONNECTED [X]"
    return "IDLE"


class DisplayState:
    """Shared mutable state the snapshot and config-change handlers both need:
    the current basic/full mode, and the last snapshot seen, so a config-only
    change (no new FMS data) can still redraw immediately instead of waiting
    for the next update.
    """

    def __init__(self, basic_mode: bool) -> None:
        self.basic_mode = basic_mode
        self.last_snapshot: StationSnapshot | None = None


def make_handlers(tracker, sink, width, height, display_state):
    def render_and_show(mode: DisplayMode, snapshot: StationSnapshot) -> None:
        if display_state.basic_mode and mode in (DisplayMode.ESTOP, DisplayMode.BYPASS):
            mode = DisplayMode.NORMAL

        team_number = team_number_text(snapshot)
        team_name = "Empty Station" if snapshot.team_id is None else (snapshot.team_nickname or "Unknown")

        print("\n--- FMS UPDATE ---")
        print(f"Mode:    {mode.name}")
        print(f"Team:    {team_number} ({team_name})")
        print(f"Status:  {status_text(mode, snapshot)}")
        print("-" * 18)

        sink.show(render(mode, snapshot, width=width, height=height, basic_mode=display_state.basic_mode))

    def handle_snapshot(snapshot: StationSnapshot) -> None:
        display_state.last_snapshot = snapshot
        changed, mode = tracker.should_redraw(snapshot)
        if not changed:
            return
        render_and_show(mode, snapshot)

    def handle_config_change(mode_value: str) -> None:
        new_basic_mode = mode_value.strip().lower() == "basic"
        if new_basic_mode == display_state.basic_mode:
            return

        display_state.basic_mode = new_basic_mode
        print(f"\n--- DISPLAY CONFIG UPDATE --- mode={'basic' if new_basic_mode else 'full'}")
        if display_state.last_snapshot is not None:
            render_and_show(compute_mode(display_state.last_snapshot), display_state.last_snapshot)

    return handle_snapshot, handle_config_change


if __name__ == "__main__":
    config = load_config()
    sink = build_sink(config)
    tracker = StateTracker()
    display_state = DisplayState(basic_mode=config.basic_mode)

    handle_snapshot, handle_config_change = make_handlers(
        tracker, sink, width=config.matrix_cols, height=config.matrix_rows, display_state=display_state
    )
    try:
        run_forever(
            config.fms_ip,
            config.target_station,
            handle_snapshot,
            on_config_change=handle_config_change,
            initial_mode="basic" if config.basic_mode else None,
        )
    finally:
        sink.close()
