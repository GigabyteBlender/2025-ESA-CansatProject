import digitalio
import board
import radio  # Assuming you have a separate `radio` module

class RadioTransmitterReceiver:
    def __init__(self):
        # Set up onboard LED
        self.led = digitalio.DigitalInOut(board.GP25)
        self.led.direction = digitalio.Direction.OUTPUT
        self.led.value = True  # Turn on LED initially
        # Packet counter
        self.packet_count = 0

    def prepare_packet(self):
        """Prepare the data packet with elapsed time and packet count."""
        return f"{self.packet_count}"

    def send_packet(self):
        """Send a packet via the radio."""
        packet = self.prepare_packet()
        try:
            radio.send(packet)  # Use your radio module's send method
            self.packet_count += 1
        except Exception as e:
            print(f"Error sending packet: {e}")

    def receive_packet(self):
        """Check for incoming packets and print them."""
        data = radio.try_read()  # Use your radio module's try_read method
        if data != None:
            try:
                decoded_data = data.decode('utf-8')
                print(decoded_data)
            except Exception as e:
                print(f"Error decoding data: {e}")

    def run(self):
        """Main loop function."""
        while True:
            self.send_packet()
            self.receive_packet()

# Create an instance of the class and start the main loop
if __name__ == "__main__":
    app = RadioTransmitterReceiver()
    app.run()
