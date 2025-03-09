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
rfm9x = adafruit_rfm9x.RFM9x(spi, cs, reset, 430.0)  # (spi, cs, reset, frequency)

def send(message):
    # Send a message
    try:
        rfm9x.send(message)
    except Exception as e:
        print(e)

def try_read():
    # Try to receive a message
    data = rfm9x.receive(timeout=1.0)
    return data# Timeout after 1 second

def rssi(rmf9x):
    # Get RSSI
    return rfm9x.rssi
