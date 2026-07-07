import json
import time
import websocket

# --- SETTINGS ---
FMS_IP = "10.0.100.5"
TARGET_STATION = "B1" 
WS_URL = f"ws://{FMS_IP}:8080/displays/alliance_station/websocket?displayId=100&station={TARGET_STATION}"


def on_message(ws, message):
    try:
        data = json.loads(message)
        
        # Filter the stream to only look at arenaStatus packets
        if data.get("type") == "arenaStatus":
            # Dig into the JSON to find Blue 1
            station_data = data["data"]["AllianceStations"][TARGET_STATION]
            
            # Extract Team Number
            team_info = station_data.get("Team")
            if team_info is not None:
                team_number = str(team_info.get("Id"))
                team_name = team_info.get("Nickname", "Unknown")
            else:
                team_number = "----"
                team_name = "Empty Station"
                
            # Extract Connection Status
            is_connected = station_data.get("DsConn") is True
            connection_text = "CONNECTED [O]" if is_connected else "DISCONNECTED [X]"
            
            # Print the results to the terminal beautifully
            print(f"\n--- FMS UPDATE ---")
            print(f"Station: {TARGET_STATION}")
            print(f"Team:    {team_number} ({team_name})")
            print(f"Status:  {connection_text}")
            print("-" * 18)
            
    except Exception as e:
        print(f"Error parsing data: {e}")

def on_error(ws, error):
    print(f"Connection Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed. Attempting to reconnect...")

def on_open(ws):
    print(f"Successfully connected to Cheesy Arena at {WS_URL}!")
    print(f"Listening for updates on station: {TARGET_STATION}...\n")

if __name__ == "__main__":
    while True:
        ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.run_forever()
        time.sleep(3)
