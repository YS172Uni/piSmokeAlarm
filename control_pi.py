import paho.mqtt.client as mqtt
import json
from datetime import datetime
from sense_hat import SenseHat
import threading
import time
import sqlite3

# ------------------------------
# MQTT Configuration
# ------------------------------
BROKER = "localhost"
PORT = 1883
USER = "dashboard"
PASSWORD = "pi2025"

# ------------------------------
# Sense HAT Setup
# ------------------------------
sense = SenseHat()
sense.clear()

# ------------------------------
# SQLite Setup
# ------------------------------
conn = sqlite3.connect('events.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node TEXT,
        event_type TEXT,   -- SENSOR / ALARM / CLEAR
        detected INTEGER,  -- 0/1 for SENSOR, NULL for ALARM/CLEAR
        timestamp TEXT
    )
''')
conn.commit()

# ------------------------------
# Node Tracking
# ------------------------------
connected_nodes = set()      # all known nodes
node_status = {}             # node_id -> 0(no smoke)/1(smoke)/-1(disconnected)
node_last_seen = {}          # node_id -> timestamp of last message
prev_detected = {}           # node_id -> previous detected state
DISCONNECT_TIMEOUT = 10      # seconds

# ------------------------------
# Process sensor messages
# ------------------------------
def process_sensor_message(msg_payload):
    data = json.loads(msg_payload)
    node_id = data["node"]
    detected = data["detected"]

    connected_nodes.add(node_id)
    node_last_seen[node_id] = time.time()
    
    # Save previous status
    prev = node_status.get(node_id, 0)
    prev_detected[node_id] = prev

    node_status[node_id] = detected

    # ------------------------------
    # Log sensor message
    # ------------------------------
    cursor.execute(
        "INSERT INTO events (node, event_type, detected, timestamp) VALUES (?, ?, ?, ?)",
        (node_id, "SENSOR", detected, datetime.now().isoformat())
    )
    conn.commit()

    print(f"{datetime.now()}: Message from {node_id}: detected={detected}")
    return detected, node_id

# ------------------------------
# Update Sense HAT display
# ------------------------------
def update_sensehat():
    pixels = []
    for node, status in node_status.items():
        if status == 0:
            color = (0, 255, 0)   # green = no smoke
        elif status == 1:
            color = (255, 0, 0)   # red = smoke
        else:
            color = (0, 0, 0)     # black = disconnected
        pixels.append(color)

    # Fill remaining LEDs
    while len(pixels) < 64:
        pixels.append((0, 0, 0))

    sense.set_pixels(pixels)

# ------------------------------
# MQTT Callback
# ------------------------------
def on_message(client, userdata, msg):
    detected, node_id = process_sensor_message(msg.payload.decode())

    # Broadcast ALARM if smoke detected
    if detected == 1:
        for node in connected_nodes:
            client.publish(f"control/{node}", "ALARM", qos=1)
            print(f"{datetime.now()}: Sent ALARM to {node}")
            # Log ALARM
            cursor.execute(
                "INSERT INTO events (node, event_type, detected, timestamp) VALUES (?, ?, ?, ?)",
                (node, "ALARM", None, datetime.now().isoformat())
            )
        conn.commit()

    # Update Sense HAT after each message
    update_sensehat()

# ------------------------------
# Node Monitor Thread
# ------------------------------
def monitor_nodes():
    while True:
        now = time.time()
        for node_id in list(node_status.keys()):
            last_seen = node_last_seen.get(node_id, 0)
            status = node_status.get(node_id, 0)

            # Node disconnected
            if now - last_seen > DISCONNECT_TIMEOUT:
                if status != -1:
                    node_status[node_id] = -1
                    for node in connected_nodes:
                        client.publish(f"control/{node}", "CLEAR", qos=1)
                        print(f"{datetime.now()}: Node {node_id} disconnected → Sent CLEAR to {node}")
                        # Log CLEAR
                        cursor.execute(
                            "INSERT INTO events (node, event_type, detected, timestamp) VALUES (?, ?, ?, ?)",
                            (node, "CLEAR", None, datetime.now().isoformat())
                        )
                    conn.commit()
            
            # Node previously in smoke state but now 0
            elif status == 0 and prev_detected.get(node_id, 0) == 1:
                for node in connected_nodes:
                    client.publish(f"control/{node}", "CLEAR", qos=1)
                    print(f"{datetime.now()}: Node {node_id} cleared → Sent CLEAR to {node}")
                    # Log CLEAR
                    cursor.execute(
                        "INSERT INTO events (node, event_type, detected, timestamp) VALUES (?, ?, ?, ?)",
                        (node, "CLEAR", None, datetime.now().isoformat())
                    )
                conn.commit()
            
        update_sensehat()
        time.sleep(1)

# ------------------------------
# MQTT Setup
# ------------------------------
client = mqtt.Client()
client.username_pw_set(USER, PASSWORD)
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.subscribe("sensors/#", qos=1)

def on_handshake(client, userdata, msg):
    if not msg.payload:#if there is no msg payload this is a clear instruction and should not trigger the callback
        return
    node_id = msg.topic.split('/')[-1]
    print(f"{datetime.now()}: Handshake received from {node_id}")
    client.publish(f"handshake/ack/{node_id}", "ACK", qos=1)#acknowledge the handshake
    connected_nodes.add(node_id)
    node_status[node_id] = 0
    node_last_seen[node_id] = time.time()
    client.publish(f"handshake/init/{node_id}", payload=None, qos=1, retain=True)#clear any handshakes

client.message_callback_add("handshake/init/#", on_handshake)
client.subscribe("handshake/init/#", qos=1)


# Start node monitoring in background
threading.Thread(target=monitor_nodes, daemon=True).start()

# Start MQTT loop
client.loop_forever()
