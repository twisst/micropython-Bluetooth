
# This is the script for the client Pico (it should be flashed with MicroPython).
# It connects to the Pico with the sensor (the server) and waits for data coming in.

# this script is in part based on Kevin McAleer's and on the examples from the aioble library:
# https://github.com/kevinmcaleer/pico_ble_remote
# https://github.com/micropython/micropython-lib/tree/master/micropython/bluetooth/aioble


import uasyncio as asyncio
import aioble
import bluetooth
import machine

led = machine.Pin("LED", machine.Pin.OUT)
connected = False
alive = False


# services identifier
SERVICES_UUID = bluetooth.UUID(0x1800)
# service identifier
SENSOR_UUID = bluetooth.UUID(0x1815)
# sensor characteristic identifier
SENSOR_CHARACTERISTICS_UUID = bluetooth.UUID(0x2A6E)


async def find_sensor():
    # Scan for 5 seconds, in active mode, with very low interval/window (to
    # maximise detection rate).
    async with aioble.scan(5000, interval_us=30000, window_us=30000, active=True) as scanner:
        async for result in scanner:
            # See if it matches our name and the sensing service.
            if result.name() == "sensor":
                print("Found sensor")
                for item in result.services():
                    print (item)
                if SERVICES_UUID in result.services():
                    print("Found sensor service")
                    return result.device
    return None


async def blink_task():
    """ Blink the LED on and off every second """
    
    toggle = True
    
    while True and alive:
        led.value(toggle)
        toggle = not toggle
        # print(f'blink {toggle}, connected: {connected}')
        if connected:
            blink = 1000
        else:
            blink = 250
        await asyncio.sleep_ms(blink)
        

async def peripheral_task():
    print('starting peripheral task')
    global connected
    connected = False
    device = await find_sensor()
    if not device:
        print("Sensor not found")
        return
    try:
        print("Connecting to", device)
        connection = await device.connect()
        
    except asyncio.TimeoutError:
        print("Timeout during connection")
        return
      
    async with connection:
        print("Connected")
        connected = True
        alive = True
        while True and alive:
            try:
                sensor_service = await connection.service(SENSOR_UUID)
                print(sensor_service)
                characteristic = await sensor_service.characteristic(SENSOR_CHARACTERISTICS_UUID)
                print(characteristic)
            except asyncio.TimeoutError:
                print("Timeout discovering services/characteristics")
                return
            while True:
                if characteristic != None:
                    try:
                        command = await characteristic.read()
                        print(f"Command: {command}")
                    except TypeError:
                        print(f'something went wrong; sensor disconnected?')
                        connected = False
                        alive = False
                        return
                    except asyncio.TimeoutError:
                        print(f'something went wrong; timeout error?')
                        connected = False
                        alive = False
                        return
                    except asyncio.GattError:
                        print(f'something went wrong; Gatt error - did the server stop?')
                        connected = False
                        alive = False
                        return
                else:
                    print('no characteristic')
                await asyncio.sleep_ms(10)



async def main():
    t1 = asyncio.create_task(blink_task())
    t2 = asyncio.create_task(peripheral_task())
    await asyncio.gather(t1, t2)

asyncio.run(main())

