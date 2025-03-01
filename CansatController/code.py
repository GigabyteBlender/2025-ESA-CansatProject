import digitalio
import board
import busio
import analogio
import time
import adafruit_dht
import adafruit_bmp280
import radio
import bmi160
import pwmio
from adafruit_motor import servo

# Constants for MQ135 sensor
VOLT_RESOLUTION = 65535  # 16-bit ADC
VCC = 5.0  # Supply voltage
RZERO = 76.63  # Resistance of sensor in clean air
PARA = 116.6020682
PARB = 2.769034857


class LED:
    """Class to control the onboard LED."""

    def __init__(self, pin):
        self.led = digitalio.DigitalInOut(pin)
        self.led.direction = digitalio.Direction.OUTPUT

    def on(self):
        self.led.value = True

    def off(self):
        self.led.value = False


class DHT11Sensor:
    """Class to handle the DHT11 temperature and humidity sensor."""

    def __init__(self, pin):
        self.sensor = adafruit_dht.DHT11(pin)

    def read_humidity(self):
        try:
            return self.sensor.humidity
        except RuntimeError as error:
            print(f"DHT11 error: {error.args[0]}")
            return None


class BMP280Sensor:
    """Class to handle the BMP280 temperature, pressure, and altitude sensor."""

    def __init__(self, i2c, sea_level_pressure=1013.25):
        self.sensor = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
        self.sensor.sea_level_pressure = sea_level_pressure

    def read_data(self):
        try:
            temperature = self.sensor.temperature
            pressure = self.sensor.pressure
            altitude = self.sensor.altitude
            return temperature, pressure, altitude
        except Exception as e:
            print(f"BMP280 error: {e}")
            return None, None, None


class MQ135Sensor:
    """Class to handle the MQ135 gas sensor."""

    def __init__(self, analog_pin):
        self.pin = analogio.AnalogIn(analog_pin)

    def read_ppm(self):
        try:
            raw_value = self.pin.value
            voltage = (raw_value / VOLT_RESOLUTION) * VCC
            rs = ((VCC - voltage) / voltage) * 1000  # Calculate resistance
            ratio = rs / RZERO
            ppm = PARA * (ratio ** -PARB)
            return ppm * 1000000  # Scale up value for better readability
        except Exception as e:
            print(f"MQ135 error: {e}")
            return None


class BMI160Sensor:
    """Class to handle the BMI160 gyroscope and accelerometer."""

    def __init__(self, i2c):
        self.sensor = bmi160.BMI160(i2c)

    def read_gyro(self):
        try:
            return self.sensor.gyro
        except Exception as e:
            print(f"BMI160 gyro error: {e}")
            return None, None, None

    def read_acceleration(self):
        try:
            return self.sensor.acceleration
        except Exception as e:
            print(f"BMI160 acceleration error: {e}")
            return None, None, None


class ServoControl:
    """Class to control two servos based on received data using adafruit_motor.servo."""

    def __init__(self, servo1_pin, servo2_pin):
        # Create PWMOut objects for the servo pins
        self.pwm1 = pwmio.PWMOut(servo1_pin, duty_cycle=2 ** 15, frequency=50)
        self.pwm2 = pwmio.PWMOut(servo2_pin, duty_cycle=2 ** 15, frequency=50)

        # Create servo objects
        self.servo1 = servo.Servo(self.pwm1)
        self.servo2 = servo.Servo(self.pwm2)

        self.previous_data = None  # Store the previous data to avoid redundant movements

    def move_servos(self, data):
        """Move the servos based on the received data (list of two angles)."""
        if data == self.previous_data:
            # print("Received same data as before, servos will not move.")
            return  # Do not move servos if the data is the same as the previous data

        try:
            # Assuming data[0] and data[1] are servo angles
            servo1_angle = data[0]
            servo2_angle = data[1]
            # Move the servos to the specified angles
            self.servo1.angle = servo1_angle
            self.servo2.angle = servo2_angle
            # Update previous data
            self.previous_data = data=

        except ValueError:
            print("Invalid data values for servo control.")
        except Exception as e:
            print(f"Servo control error: {e}")


class SensorSystem:
    """Main class to manage all sensors and data transmission."""

    def __init__(self):
        # Initialize components and sensors
        self.start_time = time.monotonic()
        # Onboard LED setup
        self.led = LED(board.GP25)
        self.led.on()  # Turn on LED to indicate system is running
        # I2C setup for BMP280 and BMI160 sensors
        i2c = busio.I2C(scl=board.GP15, sda=board.GP14)
        # Sensor initialization
        self.dht11 = DHT11Sensor(board.GP22)
        self.bmp280 = BMP280Sensor(i2c, sea_level_pressure=1024.5)
        self.mq135 = MQ135Sensor(board.GP28)
        self.bmi160 = BMI160Sensor(i2c)
        # Packet counter for radio transmission
        self.packet_count = 0
        # Servo Control
        self.servo_control = ServoControl(board.GP10, board.GP11)  # Initialize ServoControl with pins

    def collect_data(self):
        """Collect data from all sensors."""
        humidity = self.dht11.read_humidity()
        temperature, pressure, altitude = self.bmp280.read_data()
        ppm = self.mq135.read_ppm()

        gx, gy, gz = self.bmi160.read_gyro()
        ax, ay, az = self.bmi160.read_acceleration()

        if gx == 0.0 and gy == 0.0 and gz == 0.0:  # Reinitialize BMI160 if necessary
            i2c = busio.I2C(scl=board.GP15, sda=board.GP14)
            self.bmi160 = BMI160Sensor(i2c)

        return humidity, temperature, pressure, altitude, ppm, gx, gy, gz, ax, ay, az

    def format_packet(self, data):
        """Format sensor data into a packet for transmission."""
        elapsed_time = time.monotonic() - self.start_time
        # Ensure critical data is valid before sending packet
        packet = f"{elapsed_time:.2f},{data[0]:.1f},{data[1]:.1f},{data[2]:.2f},{data[3]:.1f},{data[4]:.1f},{data[5]:.3f},{data[6]:.3f},{data[7]:.3f},{data[8]:.3f},{data[9]:.3f},{data[10]:.3f}"
        return packet

    def send_packet(self, packet):
        """Send data packet via radio."""
        if packet is not None:
            radio.send(packet)
            self.packet_count += 1

    def process_radio_data(self, received_data):
        """Process the data received from the radio and move the servos."""
        try:
            data_str = received_data.decode('utf-8')
            data_list = data_str.split(',')

            # Convert the elements to numbers
            servo_data = [int(data_list[0]), int(data_list[1])]

            self.servo_control.move_servos(servo_data)

        except ValueError as e:
            print(f"Error converting radio data: {e}")
        except Exception as e:
            print(f"Error processing radio data: {e}")


# Main loop using the SensorSystem class
def main():
    system = SensorSystem()
    #infinit loop woaahhh
    while True:
        try:
            # Collect data from sensors
            data = system.collect_data()
            # Format data into a packet for transmission
            packet = system.format_packet(data)
            # Send the packet via radio module (if valid)
            system.send_packet(packet)
            # Check for incoming radio messagesss
            received_data = radio.try_read()

            if received_data is not None:
                system.process_radio_data(received_data)

        except KeyboardInterrupt:
            print("Exiting program...")
            break


if __name__ == "__main__":
    main()
