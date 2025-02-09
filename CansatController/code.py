# Import necessary libraries
import digitalio
import board
import busio
import analogio
import time
import adafruit_dht
import adafruit_bmp280
import radio
import bmi160

# timer
start_time = time.monotonic()

# Set up onboard LED
led = digitalio.DigitalInOut(board.GP25)
led.direction = digitalio.Direction.OUTPUT
led.value = True  # Turn on LED

# Initialize DHT11 temperature and humidity sensor
dhtDevice = adafruit_dht.DHT11(board.GP22)

# Set up I2C communication
i2c = busio.I2C(scl=board.GP15, sda=board.GP14)

bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
bmp280.sea_level_pressure = 1013.25  # Set sea level pressure for altitude calculation

bmi = bmi160.BMI160(i2c)

# Initialize packet counter
packet_count = 0

# Set up the analog input pin for MQ135 gas sensor
mq135_pin = analogio.AnalogIn(board.GP28)

# MQ135 sensor characteristics
VOLT_RESOLUTION = 65535  # 16-bit ADC
VCC = 5.0  # Supply voltage

# Calibration values for MQ135
RZERO = 76.63  # Resistance of sensor in clean air
PARA = 116.6020682
PARB = 2.769034857

BMP_ALT_CONST = 135

def get_gyro():
    gx, gy, gz = bmi.gyro
    return gx, gy, gz


def get_acceleration():
    ax, ay, az = bmi.acceleration
    return ax, ay, az


def get_ppm():
    """Calculate gas concentration in ppm from MQ135 sensor"""
    try:
        # Read the analog value
        raw_value = mq135_pin.value
        # Convert to voltage
        voltage = (raw_value / VOLT_RESOLUTION) * VCC
        # Convert voltage to resistance (using 1k resistor)
        rs = ((VCC - voltage) / voltage) * 1000  # 1k ohm load resistor
        # Convert to ppm
        ratio = rs / RZERO
        ppm = PARA * (ratio ** -PARB)

        return ppm * 1000000  # Multiply by 1,000,000 to scale up the value

    except Exception as e:
        print(f"Error reading MQ135 sensor: {e}")
        return None


def bmp280_read():
    """Read temperature, pressure, and altitude from BMP280 sensor"""
    try:
        pre = bmp280.pressure
        alt = bmp280.altitude
        temp = bmp280.temperature
        return temp, pre, alt
    except Exception as e:
        print(f"Error reading BMP280 sensor: {e}")
        return None, None, None


def dht_read():
    """Read humidity from DHT11 sensor"""
    try:
        humidity = dhtDevice.humidity
        return humidity
    except RuntimeError as error:
        print(f"DHT11 error: {error.args[0]}")
        return None


# Main loop
while True:
    try:
        # Reading senor data
        # dht11 data
        humidity = dht_read()

        # bmp280 data
        temperature, pressure, altitude = bmp280_read()
        altitude += BMP_ALT_CONST

        # mq135 data
        ppm = get_ppm()

        # gyro data
        gx, gy, gz = get_gyro()
        ax, ay, az = get_acceleration()

        if gx and ax == 0.0:
            bmi = bmi160.BMI160(i2c)

        # Prepare data packet
        elapsed_time = time.monotonic() - start_time
        if all((humidity, temperature, pressure, altitude, ppm)):
            packet = f"{elapsed_time:.2f},{humidity:.1f},{temperature:.1f},{pressure:.2f},{altitude:.1f},{ppm:.1f},{gx:.3f},{gy:.3f},{gz:.3f},{ax:.3f},{ay:.3f},{az:.3f}"
        else:
            packet = None

        # Send data packet via radio
        if packet is not None:
            radio.send(packet)
            # Increment packet counter
            packet_count += 1
        # Wait for 1 seconds before next reading
        time.sleep(0.5)

    except KeyboardInterrupt:
        break
