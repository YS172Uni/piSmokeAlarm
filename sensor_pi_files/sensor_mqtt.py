#!/usr/bin/env python3
import RPi.GPIO as G
import time
import json
import uuid
import threading
from datetime import datetime
import paho.mqtt.client as mqtt
from gpiozero import TonalBuzzer
from gpiozero.tones import Tone
from time import sleep

# GPIO Setup
SENSOR_PIN = 18
SPEAKER_PIN = 12

G.setmode(G.BCM)
G.setup(SENSOR_PIN, G.IN)
alarm = TonalBuzzer(SPEAKER_PIN)

def alarm_on(buzzer):
    buzzer.play(Tone(640))
    sleep(1.25)
    buzzer.play(Tone(600))
    sleep(1.25)
    buzzer.play(Tone(640))
    sleep(1.25)
    buzzer.play(Tone(600))
    sleep(1.25)

# MQTT Setup
BROKER = "10.62.134.146"  #Control Pi IP
PORT = 1883
USER = "sensor"
PASSWORD = "pi2025"
    
def create_mqtt_client(NODE_ID):#setup pi for mqtt
    client = mqtt.Client(client_id=f"sensor-{NODE_ID}")
    client.username_pw_set(USER, PASSWORD)
    return client

def connect_subscribe(client, NODE_ID):#connect/subscribe to control pi
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.subscribe(f"control/{NODE_ID}", qos=1)
    client.loop_start() 
    print(f"{datetime.now()}: Connected to Control Pi")


def on_message(client, userdata, msg):# Callback for control messages
    msg_payload = msg.payload.decode()
    print(f"{datetime.now()}: Control message received -> {msg_payload}")
    instruction_received.set()
    if msg_payload == "ALARM":
        alarm_instruction.set()
    elif msg_payload == "CLEAR":
        alarm_instruction.clear()

def publish_data(client, NODE_ID, detected):#send data to control pi
    payload = json.dumps({"node": NODE_ID, "detected": detected})
    client.publish("sensors/" + NODE_ID, payload, qos=1)

#                   Main sensor loop
NODE_ID = f"node-{uuid.uuid4()}"  #sensor node ID
client = create_mqtt_client(NODE_ID)
connect_subscribe(client, NODE_ID)
alarm_instruction = threading.Event()
instruction_received = threading.Event()

try:
    while True:
        if alarm_instruction.is_set():
            alarm_on(alarm)
        detected = 1 if G.input(SENSOR_PIN) == G.HIGH else 0
        if detected:
            print(f"{datetime.now()}: Gas Detected")
            publish_data(client, NODE_ID, detected)
            instruction_received.wait()
            instruction_received.clear()
        else:
            print(f"{datetime.now()}: Nothing Detected")        
            publish_data(client, NODE_ID, detected)
        if not alarm_instruction.is_set():
            time.sleep(5)  #check every x seconds

except KeyboardInterrupt:
    print("Exiting sensor script")
finally:
    G.cleanup()
    client.loop_stop()
    client.disconnect()
