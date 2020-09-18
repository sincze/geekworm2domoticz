#!/usr/bin/python3

#
# Raspberry UPS % 2078 /json.htm?type=command&param=udevice&idx=IDX&nvalue=0&svalue=PERCENTAGE
# Raspberry UPS V 2077 /json.htm?type=command&param=udevice&idx=IDX&nvalue=0&svalue=VOLTAGE
#
# 18-09-2020 S.Incze
#
# Usage:
# Create 2 Dummy Sensors in Domoticz Voltage & Percentage and write down the IDX
# Modify the base_url to your Domoticz machine

# Change IDX here
ups_voltage_idx = '2077'
ups_percentage_idx = '2078'

# Change Base_url here
base_url = 'http://192.168.**.**:8080'

# Debug true / false to print Debug lines
debug = 'false'

import urllib3
import json

import struct
import smbus
import sys
import time

def data_url(idx,value):
     get_url = "/json.htm?type=command&param=udevice&idx="+idx+"&nvalue=0&svalue="+value
     return get_url


def readVoltage(bus):

     address = 0x36
     read = bus.read_word_data(address, 2)
     swapped = struct.unpack("<H", struct.pack(">H", read))[0]
     voltage = swapped * 1.25 /1000/16
     return voltage


def readCapacity(bus):

     address = 0x36
     read = bus.read_word_data(address, 4)
     swapped = struct.unpack("<H", struct.pack(">H", read))[0]
     capacity = swapped/256
     return capacity


bus = smbus.SMBus(1) # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)

voltage = readVoltage(bus)
percentage = readCapacity(bus)

if debug == "true":
    print ("Voltage:%5.2fV" % readVoltage(bus))
    print ("Battery:%5i%%" % readCapacity(bus))

    print ("Voltage: "+base_url+data_url(ups_voltage_idx,str(voltage)))
    print ("Percentage: "+base_url+data_url(ups_percentage_idx,str(percentage)))

http = urllib3.PoolManager()

# Update Voltage

if voltage < 10:
   r = http.request('GET', base_url+data_url(ups_voltage_idx,str(voltage)))
   if debug == "true":
      print ("Request Status "+str(r.status))

# Update Percentage
if percentage < 100:
   r = http.request('GET', base_url+data_url(ups_percentage_idx,str(readCapacity(bus))))
   if debug == "true":
      print ("Request Status "+str(r.status))
