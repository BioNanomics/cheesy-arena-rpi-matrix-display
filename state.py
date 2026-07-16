"""Station state and display-mode priority logic."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


@dataclass
class StationSnapshot:
    team_id: Optional[int]
    team_nickname: Optional[str]
    ds_conn: bool
    estop: bool
    bypass: bool


class DisplayMode(Enum):
    ESTOP = auto()
    BYPASS = auto()
    NORMAL = auto()
    IDLE = auto()


def compute_mode(snapshot: StationSnapshot) -> DisplayMode:
    """Priority hierarchy per plan.md section 5: EStop > Bypass > Team Assigned > Idle."""
    if snapshot.estop:
        return DisplayMode.ESTOP
    if snapshot.bypass:
        return DisplayMode.BYPASS
    if snapshot.team_id is not None:
        return DisplayMode.NORMAL
    return DisplayMode.IDLE


def team_number_text(snapshot: StationSnapshot) -> str:
    """The team number as displayed/logged, or a placeholder when no team is assigned."""
    return str(snapshot.team_id) if snapshot.team_id is not None else "----"


class StateTracker:
    """Tracks the last-drawn state so callers only redraw on change."""

    def __init__(self) -> None:
        self._previous_key: Optional[tuple] = None

    def should_redraw(self, snapshot: StationSnapshot) -> tuple[bool, DisplayMode]:
        mode = compute_mode(snapshot)
        key = (mode, snapshot.team_id, snapshot.ds_conn)
        changed = key != self._previous_key
        self._previous_key = key
        return changed, mode
