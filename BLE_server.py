
# this is the script for the Pico that serves up sensor data (the server).
# (The Pico should be flashed with MicroPython.)

# this script is in part based on Kevin McAleer's and on the examples from the aioble library:
# https://github.com/kevinmcaleer/pico_ble_remote
# https://github.com/micropython/micropython-lib/tree/master/micropython/bluetooth/aioble

import sys
from micropython import const
import uasyncio as asyncio
import aioble
import bluetooth
import random
import struct
import machine

# To me this seems like insanity, but apparently every bluetooth device needs to specify
# what type of device it is and what 'service' it is providing. And it can't just be
# a word or name, it has to be a pre-defined ID from the Bluetooth specification... 
# The specification with those UUIDS can be found here: https://www.bluetooth.com/specifications/gatt/services/
# Also, some UUIDs do not seem to be valid!? ¯\_(ツ)_/¯ 

# services identifier
SERVICES_UUID = bluetooth.UUID(0x1800)

# identifier for device information service
DEVICE_UUID = bluetooth.UUID(0x180A)

# sensor service identifier
SENSOR_UUID = bluetooth.UUID(0x1815) # id for 'Automation IO service', whatever that may be.

# sensor characteristic identifier
CHARACTERISTICS_UUID = bluetooth.UUID(0x2A6E) # characteristic id for 'Temperature'

# characteristic that holds the appearance
_ADV_APPEARANCE_GENERIC_SENSOR = const(1359) # 0x054F is an identifier in the range for sensors

# Services are the types of data a device can provide. One device can provide multiple services.
# Characteristics are the data that are part of a service. Services can contain several different characteristics.


# to blink built-in LED fast of slow depending on if there is a connection
led = machine.Pin("LED", machine.Pin.OUT) 

_ADV_INTERVAL_MS = 250_000 # How frequently to send advertising beacons.

connection = None


# send out device information (not sure if this all is actually necessary):
def uid():
    """ Return the unique id of the device as a string """
    return "{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}".format(
        *machine.unique_id())
# Create service for device info
device_info = aioble.Service(DEVICE_UUID)
# Create characteristics for device info
SERIAL_NUMBER_ID = const(0x2A25)
HARDWARE_REVISION_ID = const(0x2A26)
aioble.Characteristic(device_info, bluetooth.UUID(SERIAL_NUMBER_ID), read=True, initial=uid())
aioble.Characteristic(device_info, bluetooth.UUID(HARDWARE_REVISION_ID), read=True, initial=sys.version)


# Register GATT server
service = aioble.Service(SENSOR_UUID)
sensor_characteristic = aioble.Characteristic(
    service, CHARACTERISTICS_UUID, read=True, notify=True
)
aioble.register_services(service, device_info)

connected = False


# This would be periodically polling a hardware sensor.
async def sensor_task():
    t = 24.5
    while True:
        if not connected:
            print('not connected')
            await asyncio.sleep_ms(1000)
            continue
        sensor_characteristic.write(struct.pack("<h", int(t * 100))) # encode sensor value t as sint16
        sensor_characteristic.notify(connection,b"a") # is this necessary?
        t += random.uniform(-0.5, 0.5)
        await asyncio.sleep_ms(1000) # wait one second


# Wait for connections. Don't advertise while a central is connected.
async def peripheral_task():
    global connected, connection
    while True:
        connected = False
        async with await aioble.advertise(
            _ADV_INTERVAL_MS,
            name="sensor", # name with which to advertise this Bluetooth-enabled device
            services=[SERVICES_UUID],
            appearance=_ADV_APPEARANCE_GENERIC_SENSOR,
        ) as connection:
            print("Connection from", connection.device)
            connected = True
            await connection.disconnected()
            print(f'disconnected')
    

async def blink_task():
    print('blink task started')
    toggle = True
    while True:
        led.value(toggle)
        toggle = not toggle
        blink = 1000
        if connected:
            blink = 1000
        else:
            blink = 250
        await asyncio.sleep_ms(blink)

# Run tasks
async def main():
    t1 = asyncio.create_task(sensor_task())
    t2 = asyncio.create_task(peripheral_task())
    t3 = asyncio.create_task(blink_task())
    await asyncio.gather(t1, t2, t3)


asyncio.run(main())

