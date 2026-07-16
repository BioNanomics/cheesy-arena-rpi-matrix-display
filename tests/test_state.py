from state import DisplayMode, StateTracker, StationSnapshot, compute_mode


def snapshot(**overrides):
    defaults = dict(team_id=9431, team_nickname="Refinery", ds_conn=True, estop=False, bypass=False)
    defaults.update(overrides)
    return StationSnapshot(**defaults)


def test_estop_takes_priority_over_everything():
    assert compute_mode(snapshot(estop=True, bypass=True)) == DisplayMode.ESTOP


def test_bypass_takes_priority_over_normal():
    assert compute_mode(snapshot(bypass=True)) == DisplayMode.BYPASS


def test_normal_when_team_assigned():
    assert compute_mode(snapshot()) == DisplayMode.NORMAL


def test_idle_when_no_team_assigned():
    assert compute_mode(snapshot(team_id=None)) == DisplayMode.IDLE


def test_tracker_only_flags_redraw_on_change():
    tracker = StateTracker()

    changed, mode = tracker.should_redraw(snapshot())
    assert changed is True
    assert mode == DisplayMode.NORMAL

    changed, mode = tracker.should_redraw(snapshot())
    assert changed is False

    changed, mode = tracker.should_redraw(snapshot(ds_conn=False))
    assert changed is True
