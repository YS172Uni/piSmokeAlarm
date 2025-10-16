import paho.mqtt.client as mqtt
import json
from datetime import datetime

BROKER = "localhost"
PORT = 1883
USER = "dashboard"
PASSWORD = "pi2025"

# Keep track of all connected sensor nodes
nodes_seen = set()

def process_sensor_message(msg_payload):
    data = json.loads(msg_payload)
    node_id = data["node"]
    detected = data["detected"]
    print(f"{datetime.now()}: Message from {node_id}: detected={detected}")

    nodes_seen.add(node_id)  # remember this node

    if detected == 1:
        return "ALARM"
    else:
        return "NO_ACTION"

def on_message(client, userdata, msg):
    response = process_sensor_message(msg.payload.decode())

    if response == "ALARM":
        for node in nodes_seen:  # broadcast ALARM to all known nodes
            client.publish(f"control/{node}", "ALARM", qos=1)
            print(f"{datetime.now()}: Sent ALARM to {node}")
    else:
        print(f"{datetime.now()}: No action required")

client = mqtt.Client()
client.username_pw_set(USER, PASSWORD)
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.subscribe("sensors/#", qos=1)  # subscribe to all sensors
client.loop_forever()

