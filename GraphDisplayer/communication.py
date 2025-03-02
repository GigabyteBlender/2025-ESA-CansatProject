import serial
import random
import serial.tools.list_ports
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Communication:
    """Handles serial communication with a device."""

    def __init__(self, port_name=None, baudrate=9600):  # Port name can be None initially
        """
        Initializes the serial communication.

        Args:
            port_name (str): The serial port name.
            baudrate (int): The baud rate.
        """
        self.baudrate = baudrate
        self.portName = port_name
        self.dummyPlug = False
        self.ser = None  # Initialize ser to None

        if self.portName:
            self.connect_serial()

    def connect_serial(self):
        """Connects to the serial port."""
        try:
            self.ser = serial.Serial(self.portName, self.baudrate, timeout=1)
            self.com_serial = serial.Serial("/dev/cu.usbmodem14203", self.baudrate, timeout=1)

            logging.info(f"Connected to {self.portName} at {self.baudrate} baud.")
            logging.info(self.ser)
            logging.info(self.com_serial)
            
        except serial.serialutil.SerialException as e:
            logging.error(f"Could not open port {self.portName}: {e}")
            self.dummyPlug = True
            logging.warning("Dummy mode activated")

    def close(self):
        """Closes the serial port if it's open."""
        if self.ser and self.ser.isOpen():
            self.ser.close()
            self.com_serial.close()
            logging.info(f"Closed port {self.portName}")
        else:
            logging.info(f"Port {self.portName} is already closed or was never opened.")

    def serial_send(self, data: str):
        """
        Sends data to the serial port.

        Args:
            data (str): The data to be sent.
        """
        if self.dummyPlug:
            logging.warning("Dummy mode active. Data not sent.")
            return
        try:
            message = data # Create the message
            logging.info(message)
            self.com_serial.write(message.encode('utf-8')) # Send the message
        except serial.SerialException as e:
            logging.error(f"Error sending data to serial port: {e}")

    def getData(self):
        """
        Reads data from the serial port.

        Returns:
            list: A list of data values or an empty list if no data is available.
        """
        if self.dummyPlug:
            return [float(random.randint(0, 100)) for _ in range(12)]

        if not self.ser:
            logging.warning("Serial port not initialized. Returning empty list.")
            return []

        try:
            if self.ser.in_waiting > 0:
                value = self.ser.readline()
                decoded_bytes = value.decode("utf-8").strip()
                value_chain = decoded_bytes.split(",")
                try:
                    value_chain = [float(x) for x in value_chain]
                except ValueError:
                    logging.warning(f"Invalid data format received: {value_chain}")
                    return []

                return value_chain
            else:
                return []  # No data available
        except serial.SerialException as e:
            logging.error(f"Error reading from serial port: {e}")
            return []

    def isOpen(self):
        """Checks if the serial port is open."""
        return self.ser is not None and self.ser.isOpen()

    def dummyMode(self):
        """Checks if dummy mode is active."""
        return self.dummyPlug

