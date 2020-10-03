#!/usr/bin/python3
#
# Raspberry UPS % 2078 /json.htm?type=command&param=udevice&idx=IDX&nvalue=0&svalue=PERCENTAGE
# Raspberry UPS V 2077 /json.htm?type=command&param=udevice&idx=IDX&nvalue=0&svalue=VOLTAGE
# Raspberry UPS V 162  /json.htm?type=command&param=udevice&idx=IDX&nvalue=0&svalue=TEMP
#
# 18-09-2020 S.Incze
# 01-10-2020 S.Incze added HTTPS & CPU Temp & CPU Usage
#
# Usage:
# Create 4 Dummy Sensors in Domoticz and write down the IDX
# - Voltage (UPS Voltage) 
# - Percentage (UPS Capacity, CPU Usage)
# - Temp Sensor (Raspberry temp)
#
# Modify the base_url to your Domoticz machine
#
# Requires:
#
# -
#

# Change IDX here
ups_voltage_idx = '2077'
ups_percentage_idx = '2078'
ups_cpu_temp_idx = '162'
ups_cpu_usage_idx = '1516' # https://www.raspberrypi.org/forums/viewtopic.php?t=22180

# In my case I need to login to Domoticz && use a valid SSL certificate
username = ''
password = ''

# Change Base_url here
#base_url = 'http://x.x.x.x:8080'
base_url = "https://proxy.me.nl:1234"  # Due to VLAN settings need to use proxy

# Debug true / false to print Debug lines
debug = 'true'

####################################################################################
## NO CHANGES BELOW THIS POINT
####################################################################################

import urllib3
import json
import struct
import smbus
import sys
import time
import os

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


def auth_header():

    headers = urllib3.make_headers(basic_auth=username+':'+password)
    return headers


def get_cpu_temp():
    """
    Obtains the current value of the CPU temperature.
    :returns: Current value of the CPU temperature if successful, zero value otherwise.
    :rtype: float
    """
    # Initialize the result.
    result = 0.0
    # The first line in this file holds the CPU temperature as an integer times 1000.
    # Read the first line and remove the newline character at the end of the string.
    with open('/sys/class/thermal/thermal_zone0/temp') as f:
        line = f.readline().strip()
    # Test if the string is an integer as expected.
    if line.isdigit():
        # Convert the string with the CPU temperature to a float in degrees Celsius.
        result = float(line) / 1000
    # Give the result back to the caller.
    return result


# Return % of CPU used by user as a character string
def getCPUuse():

   result = str(os.popen("top -n1 | awk '/Cpu\(s\):/ {print $2}'").readline()).rstrip()
   return result

#####################################################################################
# Reading all the values
#####################################################################################

bus = smbus.SMBus(1) # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
voltage = readVoltage(bus)
percentage = readCapacity(bus)
temp = get_cpu_temp()
cpu = getCPUuse() # https://www.raspberrypi.org/forums/viewtopic.php?t=22180


if debug == "true":
    print ("Voltage:%5.2fV" % readVoltage(bus))
    print ("Battery:%5i%%" % readCapacity(bus))
    print ('CPU Usage: '+cpu)
    print ("Temperature: "+base_url+data_url(ups_cpu_temp_idx,str(temp)))
    print ("CPU Usage: "+base_url+data_url(ups_cpu_usage_idx,str(cpu)))
    print ("Voltage: "+base_url+data_url(ups_voltage_idx,str(voltage)))
    print ("Percentage: "+base_url+data_url(ups_percentage_idx,str(percentage)))

#####################################################################################
# Sending values to Domoticz
#####################################################################################
http = urllib3.PoolManager()

# Update Voltage

if voltage < 10:
   r = http.request('GET', base_url+data_url(ups_voltage_idx,str(voltage)),headers=auth_header())
   if debug == "true":
      print ("Request Status "+str(r.status))

# Update Percentage

if percentage < 100:
   r = http.request('GET', base_url+data_url(ups_percentage_idx,str(readCapacity(bus))),headers=auth_header())

   if debug == "true":
      print ("Request Status "+str(r.status))

# Update Temperature

if temp > 1 and temp < 100:
   r = http.request('GET', base_url+data_url(ups_cpu_temp_idx,str(temp)),headers=auth_header())

   if debug == "true":
      print ("Request Status "+str(r.status))

# Update CPU Usage

   r = http.request('GET', base_url+data_url(ups_cpu_usage_idx,str(cpu)),headers=auth_header())

   if debug == "true":
      print ("Request Status "+str(r.status))
