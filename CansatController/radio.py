import digitalio
import board
import busio
import adafruit_rfm9x

# SPI setup
spi = busio.SPI(clock=board.GP2, MOSI=board.GP3, MISO=board.GP4)

# Radio pins
cs = digitalio.DigitalInOut(board.GP6)  # Chip select
reset = digitalio.DigitalInOut(board.GP7)  # Reset pin

# Initialize RFM9x radio
rfm9x = adafruit_rfm9x.RFM9x(spi, cs, reset, 433.0)  # (spi, cs, reset, frequency)
print("radio ready")


def send(message):
    # Send a message
    print(message)
    rfm9x.send(message)


def try_read(rmf9x):
    # Try to receive a message
    return rfm9x.recieve(timeout=1.0)  # Timeout after 1 second


def rssi(rmf9x):
    # Get RSSI
    return rfm9x.rssi
