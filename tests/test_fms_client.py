import json
import os

import pytest

from fms_client import handle_message, parse_station_snapshot
from state import StationSnapshot

FIXTURES_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "arena_status_samples.json")

with open(FIXTURES_PATH) as f:
    FIXTURES = json.load(f)


def parse(name: str) -> StationSnapshot:
    return parse_station_snapshot(json.dumps(FIXTURES[name]), "B1")


def test_ds_conn_is_parsed_from_the_correct_key():
    # Regression test: fms_ws_test.py originally read "sConn" instead of
    # "DsConn", which plan.md's own example payload uses. This must stay
    # True for a payload with DsConn: true.
    snapshot = parse("normal_connected")
    assert snapshot.ds_conn is True


def test_ds_conn_false_when_disconnected():
    snapshot = parse("normal_disconnected")
    assert snapshot.ds_conn is False


def test_estop_and_bypass_parsed():
    assert parse("estop").estop is True
    assert parse("bypass").bypass is True


def test_team_fields_parsed():
    snapshot = parse("normal_connected")
    assert snapshot.team_id == 9431
    assert snapshot.team_nickname == "Refinery"


def test_idle_has_no_team():
    snapshot = parse("idle")
    assert snapshot.team_id is None


def test_non_arena_status_message_returns_none():
    message = json.dumps({"type": "something_else", "data": {}})
    assert parse_station_snapshot(message, "B1") is None


def test_missing_station_returns_none():
    message = json.dumps(FIXTURES["normal_connected"])
    assert parse_station_snapshot(message, "R1") is None


def test_missing_station_logs_a_warning(capsys):
    # Regression test: a misconfigured/typo'd station used to fail silently
    # (no console output at all), unlike the original prototype which
    # printed a visible error on every such message.
    message = json.dumps(FIXTURES["normal_connected"])
    parse_station_snapshot(message, "R1")
    assert "R1" in capsys.readouterr().out


def test_nickname_defaults_to_unknown_when_missing():
    # Regression test: the original prototype defaulted a missing Nickname
    # to "Unknown"; that default was dropped when parsing moved here.
    payload = json.loads(json.dumps(FIXTURES["normal_connected"]))
    del payload["data"]["AllianceStations"]["B1"]["Team"]["Nickname"]
    snapshot = parse_station_snapshot(json.dumps(payload), "B1")
    assert snapshot.team_nickname == "Unknown"


def test_handle_message_does_not_propagate_on_snapshot_errors():
    # Regression test: errors raised inside on_snapshot (e.g. a rendering or
    # hardware failure) used to be uncaught, propagating out of the
    # websocket message handler and looking like a connection failure.
    message = json.dumps(FIXTURES["normal_connected"])

    def failing_on_snapshot(_snapshot):
        raise RuntimeError("boom")

    handle_message(message, "B1", failing_on_snapshot)  # must not raise


def test_handle_message_calls_on_snapshot_for_valid_data():
    message = json.dumps(FIXTURES["normal_connected"])
    received = []

    handle_message(message, "B1", received.append)

    assert len(received) == 1
    assert received[0].team_id == 9431
