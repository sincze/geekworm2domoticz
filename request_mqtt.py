#!/home/pi/mqttenv/bin/python

############################################################################################################
# A Project of TNET Services, Inc
#
# Title:     X728 UPS Monitor for Home Assistant
# Author:    S. Incze
# Project:   Raspberry Pi - UPS Monitoring
#
# Copyright: Copyright (c) 2025 S. Incze
#
# Purpose:
#
# This Python script reads battery voltage, capacity, CPU temperature, and CPU usage
# from a Raspberry Pi with a Geekworm X728 UPS HAT. It publishes this data via MQTT
# using Home Assistant's MQTT Discovery format, allowing automatic sensor creation.
#
# Features:
# - I2C-based voltage and capacity readings from the UPS
# - CPU temperature and usage monitoring
# - Auto-detection of hostname for MQTT topic scoping
# - Configurable MQTT prefix and broker
# - Supports Home Assistant auto-discovery
# - Optional debug logging
#
# Installation Instructions:
#
# 1. Enable I2C on the Raspberry Pi using `raspi-config` or manually.
#
# 2. Install required packages:
#    sudo apt update
#    sudo apt install python3-venv python3-smbus i2c-tools
#
# 3. Create and activate Python virtual environment:
#    python3 -m venv ~/mqttenv
#    source ~/mqttenv/bin/activate
#    pip install paho-mqtt==1.6.1 smbus
#
# 4. Place this script where you'd like to run it from, e.g., /home/pi/scripts/x728_monitor.py
#    Make it executable:
#    chmod +x /home/pi/scripts/x728_monitor.py
#
# 5. (Optional) Test I2C connection:
#    sudo i2cdetect -y 1     # You should see address 0x36
#
# 6. Add to crontab for periodic updates (every minute, for example):
#    crontab -e
#    * * * * * /home/pi/mqttenv/bin/python /home/pi/scripts/x728_monitor.py
#
############################################################################################################

import os
import json
import struct
import socket
import logging
import smbus
import subprocess
import paho.mqtt.client as mqtt
import time
import re

# ---- Configuration ----
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
MQTT_PREFIX = "geekworm"

MANUFACTURER = "Geekworm"
MODEL = "X728"

DEBUG = True  # Enable debug printout

# ---- Generate Host Slug ----
hostname = socket.gethostname()
#HOST_SLUG = hostname.strip().lower().replace(" ", "_")
HOST_SLUG = re.sub(r"[^a-zA-Z0-9_-]", "_", hostname.strip().lower())

# Device-specific name and slug
DEVICE_NAME = f"X728 UPS ({hostname})"
DEVICE_SLUG = "x728_ups"
DEVICE_UNIQUE = f"{DEVICE_SLUG}_{HOST_SLUG}"

# MQTT topics
STATE_TOPIC = f"{MQTT_PREFIX}/sensor/{HOST_SLUG}/{DEVICE_SLUG}/state"

# ---- MQTT Setup ----
client = mqtt.Client(protocol=mqtt.MQTTv311)
client.enable_logger()

client.on_connect = lambda *args: None
client.on_disconnect = lambda *args: None
client.on_publish = lambda *args: None

client.connect(MQTT_BROKER, MQTT_PORT, 60)
time.sleep(1)  # Give MQTT time to connect

device_info = {
    "identifiers": [DEVICE_UNIQUE],
    "name": DEVICE_NAME,
    "manufacturer": MANUFACTURER,
    "model": MODEL
}

# ---- Sensor Configurations ----
def publish_discovery(sensor_type, unit, value_template, device_class, unique_id, name):
    topic = f"homeassistant/sensor/{HOST_SLUG}_{DEVICE_SLUG}_{sensor_type}/config"
    payload = {
        "name": name,
        "state_topic": STATE_TOPIC,
        "unit_of_measurement": unit,
        "value_template": value_template,
        "device_class": device_class,
        "unique_id": unique_id,
        "device": device_info
    }
    if DEBUG:
        print(f"[DEBUG] Publishing config to {topic}: {payload}")
    client.publish(topic, json.dumps(payload), retain=True)

# ---- Read Sensor Values ----
def readVoltage(bus):
    address = 0x36
    read = bus.read_word_data(address, 2)
    swapped = struct.unpack("<H", struct.pack(">H", read))[0]
    return round(swapped * 1.25 / 1000 / 16, 2)

def readCapacity(bus):
    address = 0x36
    read = bus.read_word_data(address, 4)
    swapped = struct.unpack("<H", struct.pack(">H", read))[0]
    return round(swapped / 256)

def get_cpu_temp():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            line = f.readline().strip()
        return float(line) / 1000 if line.isdigit() else 0.0
    except:
        return 0.0

def get_cpu_usage():
    usage = os.popen("top -bn1 | grep 'Cpu(s)'").readline()
    try:
        return round(float(usage.split('%')[0].split()[-1]), 1)
    except:
        return 0.0

def get_system_voltage():
    try:
        result = subprocess.check_output(["vcgencmd", "measure_volts", "core"]).decode().strip()
        voltage = float(result.replace("volt=", "").replace("V", ""))
        return round(voltage, 2)
    except:
        return 0.0

# ---- Initialize Sensors ----
bus = smbus.SMBus(1)
voltage = readVoltage(bus)
capacity = readCapacity(bus)
temperature = get_cpu_temp()
cpu_usage = get_cpu_usage()
system_voltage = get_system_voltage()

# ---- Publish Discovery Configs ----
publish_discovery("voltage", "V", "{{ value_json.voltage }}", "voltage", f"{HOST_SLUG}_{DEVICE_SLUG}_voltage", "Battery Voltage")
publish_discovery("capacity", "%", "{{ value_json.capacity }}", "battery", f"{HOST_SLUG}_{DEVICE_SLUG}_capacity", "Battery Capacity")
publish_discovery("temperature", "°C", "{{ value_json.cpu_temp }}", "temperature", f"{HOST_SLUG}_{DEVICE_SLUG}_cpu_temp", "CPU Temperature")
publish_discovery("cpu_usage", "%", "{{ value_json.cpu_usage }}", "power_factor", f"{HOST_SLUG}_{DEVICE_SLUG}_cpu_usage", "CPU Usage")
publish_discovery("system_voltage", "V", "{{ value_json.system_voltage }}", "voltage", f"{HOST_SLUG}_{DEVICE_SLUG}_system_voltage", "System Voltage")

# ---- Publish Current State ----
state_payload = {
    "voltage": voltage,
    "capacity": capacity,
    "cpu_temp": temperature,
    "cpu_usage": cpu_usage,
    "system_voltage": system_voltage
}

if DEBUG:
    print(f"[DEBUG] Publishing state to {STATE_TOPIC}: {state_payload}")

client.publish(STATE_TOPIC, json.dumps(state_payload), retain=False)
# --- Give MQTT time to send before disconnecting ---
time.sleep(0.1)
client.disconnect()
