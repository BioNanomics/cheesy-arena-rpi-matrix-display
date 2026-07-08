import json
import time
import websocket

# --- SETTINGS ---
FMS_IP = "10.0.100.5" # Can change depending on FMS Setup
TARGET_STATION = "B1" 
WS_URL = f"ws://{FMS_IP}:8080/displays/alliance_station/websocket?displayId=100&station={TARGET_STATION}"

# Memory to track state changes
previous_state = None

def on_message(ws, message):
    global previous_state
    
    try:
        data = json.loads(message)
        
        # Filter the stream to only look at arenaStatus packets
        if data.get("type") == "arenaStatus":
            # Dig into the JSON to find the target station
            station_data = data["data"]["AllianceStations"][TARGET_STATION]
            
            # Extract Team Number
            team_info = station_data.get("Team")
            if team_info is not None:
                team_number = str(team_info.get("Id"))
                team_name = team_info.get("Nickname", "Unknown")
            else:
                team_number = "----"
                team_name = "Empty Station"
                
            # Extract Status Booleans (Including E-Stop and Bypass)
            is_connected = station_data.get("sConn") is True
            is_estop = station_data.get("EStop") is True
            is_bypassed = station_data.get("Bypass") is True
            
            # Bundle the variables into a single state string
            current_state = f"{team_number}_{is_connected}_{is_estop}_{is_bypassed}"
            
            # Only print/draw if the state changed
            if current_state != previous_state:
                
                # Determine what status text to show in the console
                if is_estop:
                    status_text = "!!! ESTOPPED !!!"
                elif is_bypassed:
                    status_text = "BYPASSED"
                else:
                    status_text = "CONNECTED [O]" if is_connected else "DISCONNECTED [X]"
                
                # Print the results to the terminal
                print(f"\n--- FMS UPDATE ---")
                print(f"Station: {TARGET_STATION}")
                print(f"Team:    {team_number} ({team_name})")
                print(f"Status:  {status_text}")
                print("-" * 18)
                
                # Save this new state into memory for the next loop
                previous_state = current_state
                
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
