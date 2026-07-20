"""Websocket connection to the Cheesy Arena FMS and payload parsing."""

import json
import time
from typing import Callable, Optional
from urllib.parse import urlparse, parse_qs

import websocket

from state import StationSnapshot


def parse_display_configuration(message: str) -> Optional[str]:
    """Parse a displayConfiguration message and return its "mode" query param.

    Cheesy Arena sends this whenever an admin edits this display's row on the
    Setup -> Displays page -- the live, in-Cheesy-Arena equivalent of editing
    a local config file. Returns None if the message isn't a
    displayConfiguration packet at all; returns "" (not None) if it is one
    but the admin cleared/never set "mode", so callers can tell "not
    applicable" apart from "explicitly reset to the default".
    """
    data = json.loads(message)

    if data.get("type") != "displayConfiguration":
        return None

    url = data.get("data", "")
    params = parse_qs(urlparse(url).query, keep_blank_values=True)
    values = params.get("mode", [""])
    return values[0] if values else ""


def parse_station_snapshot(message: str, station: str) -> Optional[StationSnapshot]:
    """Parse a raw arenaStatus websocket message into a StationSnapshot.

    Returns None if the message isn't an arenaStatus packet or doesn't
    contain data for the requested station.
    """
    data = json.loads(message)

    if data.get("type") != "arenaStatus":
        return None

    station_data = data.get("data", {}).get("AllianceStations", {}).get(station)
    if station_data is None:
        print(f"Warning: no data for station '{station}' in arenaStatus payload")
        return None

    team_info = station_data.get("Team")
    if team_info is not None:
        team_id = team_info.get("Id")
        team_nickname = team_info.get("Nickname", "Unknown")
    else:
        team_id = None
        team_nickname = None

    return StationSnapshot(
        team_id=team_id,
        team_nickname=team_nickname,
        ds_conn=station_data.get("DsConn") is True,
        estop=station_data.get("EStop") is True,
        bypass=station_data.get("Bypass") is True,
        alliance="red" if station[:1].upper() == "R" else "blue",
    )


def build_ws_url(fms_ip: str, station: str, display_id: int = 100, initial_mode: Optional[str] = None) -> str:
    url = f"ws://{fms_ip}:8080/displays/alliance_station/websocket?displayId={display_id}&station={station}"
    if initial_mode:
        # Seeds this display's Configuration on Cheesy Arena's Setup -> Displays
        # page with our local startup default, so the admin UI and the Pi agree
        # on the starting mode before anyone edits it live.
        url += f"&mode={initial_mode}"
    return url


def handle_message(
    message: str,
    station: str,
    on_snapshot: Callable[[StationSnapshot], None],
    on_config_change: Optional[Callable[[str], None]] = None,
) -> None:
    """Parse a raw message and invoke on_snapshot or on_config_change, guarding
    against any error (malformed payload, or a failure inside a callback's own
    rendering/hardware code) so a single bad message can't kill the websocket
    connection.
    """
    try:
        snapshot = parse_station_snapshot(message, station)
        if snapshot is not None:
            on_snapshot(snapshot)
            return

        if on_config_change is not None:
            mode = parse_display_configuration(message)
            if mode is not None:
                on_config_change(mode)
    except Exception as exc:
        print(f"Error handling message: {exc}")


def run_forever(
    fms_ip: str,
    station: str,
    on_snapshot: Callable[[StationSnapshot], None],
    reconnect_delay: float = 3.0,
    on_config_change: Optional[Callable[[str], None]] = None,
    initial_mode: Optional[str] = None,
) -> None:
    """Connect to the FMS and invoke on_snapshot for every parsed update, and
    on_config_change whenever the display's live Configuration is edited from
    Cheesy Arena's Setup -> Displays page.

    Reconnects automatically if the connection drops or the FMS restarts.
    """
    ws_url = build_ws_url(fms_ip, station, initial_mode=initial_mode)

    def on_message(_ws: websocket.WebSocketApp, message: str) -> None:
        handle_message(message, station, on_snapshot, on_config_change)

    def on_error(_ws: websocket.WebSocketApp, error: Exception) -> None:
        print(f"Connection Error: {error}")

    def on_close(_ws: websocket.WebSocketApp, close_status_code, close_msg) -> None:
        print("WebSocket closed. Attempting to reconnect...")

    def on_open(_ws: websocket.WebSocketApp) -> None:
        print(f"Successfully connected to Cheesy Arena at {ws_url}!")
        print(f"Listening for updates on station: {station}...\n")

    while True:
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        ws.run_forever()
        time.sleep(reconnect_delay)
