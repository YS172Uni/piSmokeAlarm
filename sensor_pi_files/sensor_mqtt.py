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
alarm_instruction = threading.Event()
instruction_received = threading.Event()
connected_event = threading.Event()
    
def create_mqtt_client(NODE_ID):#setup pi for mqtt
    client = mqtt.Client(client_id=f"sensor-{NODE_ID}")
    client.username_pw_set(USER, PASSWORD)
    return client

def on_message(client, userdata, msg):# Callback for control messages
    msg_payload = msg.payload.decode()
    print(f"{datetime.now()}: Control message received -> {msg_payload}")
    instruction_received.set()
    if msg_payload == "ALARM":
        alarm_instruction.set()
    elif msg_payload == "CLEAR":
        alarm_instruction.clear()

def on_connect(client, userdata, flags, rc):
    NODE_ID = userdata
    if rc == 0:
        print(f"{datetime.now()}: Connected to Control Pi")
        client.subscribe(f"control/{NODE_ID}", qos=1)
        connected_event.set()
    else:
        print(f"{datetime.now()}: Could not connect to Control Pi - rc = {rc}")

def connect_subscribe(client, NODE_ID):
    print("Attempting Connection with Control Pi")
    client.on_message = on_message
    client.on_connect = on_connect
    client.user_data_set(NODE_ID)
    client.loop_start()
    try:
        client.connect(BROKER, PORT, 60)
    except Exception as e:
        print(f"MQTT connection failed: {e}")

    connected = connected_event.wait(timeout=10)
    if connected:
        print("Remote Control Mode")
    else:
        print("Local Mode")
    return connected

def publish_data(client, NODE_ID, detected):#send data to control pi
    payload = json.dumps({"node": NODE_ID, "detected": detected})
    client.publish("sensors/" + NODE_ID, payload, qos=1)

#                   Main sensor loop
NODE_ID = f"node-{uuid.uuid4()}"  #sensor node ID
client = create_mqtt_client(NODE_ID)
connected = connect_subscribe(client, NODE_ID)

try:
    while True:
        if connected:#loop for if pi is connected
            if alarm_instruction.is_set():
                alarm_on(alarm)
            detected = 1 if G.input(SENSOR_PIN) == G.HIGH else 0
            if detected:
                print(f"{datetime.now()}: Gas Detected")
                publish_data(client, NODE_ID, detected)
                got_instruction = instruction_received.wait(timeout=3)
                instruction_received.clear()
                if not got_instruction:
                    connected = False
                    continue
            else:
                print(f"{datetime.now()}: Nothing Detected")        
                publish_data(client, NODE_ID, detected)
            if not alarm_instruction.is_set():
                time.sleep(5)  #check every x seconds
        else:#loop for local operations
            detected = 1 if G.input(SENSOR_PIN) == G.HIGH else 0
            if detected:
                print(f"{datetime.now()}: Gas Detected")
                alarm_on(alarm)
            else:
                print(f"{datetime.now()}: Nothing Detected")        
                time.sleep(5)  #check every x seconds

except KeyboardInterrupt:
    print("Exiting sensor script")
finally:
    G.cleanup()
    client.loop_stop()
    client.disconnect()
