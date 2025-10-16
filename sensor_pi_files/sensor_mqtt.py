#!/usr/bin/env python3
import RPi.GPIO as G
import time
import json
import uuid
from datetime import datetime
import paho.mqtt.client as mqtt

# GPIO Setup
SENSOR_PIN = 18
SPEAKER_PIN = 12

G.setmode(G.BCM)
G.setup(SENSOR_PIN, G.IN)
G.setup(SPEAKER_PIN, G.OUT)

# MQTT Setup
BROKER = "10.62.134.146"  #control Pi IP
PORT = 1883
USER = "sensor"
PASSWORD = "pi2025"

NODE_ID = f"node-{uuid.uuid4()}"  #sensor node ID

client = mqtt.Client(client_id=f"sensor-{NODE_ID}")
client.username_pw_set(USER, PASSWORD)

# Connect to broker
client.connect(BROKER, PORT, 60)

# Callback for control messages
def on_message(client, userdata, msg):
    msg_payload = msg.payload.decode()
    print(f"{datetime.now()}: Control message received -> {msg_payload}")
    if msg_payload == "ALARM":
        #this is pwm, needs to be adjusted accordinly
        G.output(SPEAKER_PIN, G.HIGH)
        time.sleep(1)
        G.output(SPEAKER_PIN, G.LOW)

client.on_message = on_message
client.subscribe(f"control/{NODE_ID}", qos=1)
client.loop_start()  # Run network loop in background

# Main sensor loop
try:
    while True:
        detected = 1 if G.input(SENSOR_PIN) == G.HIGH else 0
        if detected:
            print(f"{datetime.now()}: Butane/LPG Detected")
        else:
            print(f"{datetime.now()}: Nothing Detected")

        #publish sensor state to control pi
        payload = json.dumps({"node": NODE_ID, "detected": detected})
        client.publish("sensors/" + NODE_ID, payload, qos=1)

        time.sleep(5)  #check every x seconds

except KeyboardInterrupt:
    print("Exiting sensor script")
finally:
    G.cleanup()
    client.loop_stop()
    client.disconnect()
