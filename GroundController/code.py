# Import necessary libraries
import digitalio
import board
import busio
import analogio
import time
import radio

# timer
start_time = time.monotonic()

# Set up onboard LED
led = digitalio.DigitalInOut(board.GP25)
led.direction = digitalio.Direction.OUTPUT
led.value = True  # Turn on LED

# Initialize packet counter
packet_count = 0
# Main loop
while True:
    # Prepare data packet
    elapsed_time = time.monotonic() - start_time

    packet = "test"

    # Send data packet via radio
    if packet is not None:
        radio.send(packet)
        # Increment packet counter
        packet_count += 1

    data = radio.try_read()
    if data is not None:
        data = data.decode('utf-8')
        print(data)
