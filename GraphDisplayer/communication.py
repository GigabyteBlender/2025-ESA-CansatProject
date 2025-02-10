import serial
import random
import serial.tools.list_ports

class Communication:
    baudrate = ''
    portName = ''
    dummyPlug = False
    ports = serial.tools.list_ports.comports()
    ser = serial.Serial()

    def __init__(self):
        self.baudrate = 115200
        print("the available ports are (if none appear, press any letter): ")
        for port in sorted(self.ports):
            # getting com list: https://stackoverflow.com/a/52809180
            print(("{}".format(port)))
        try:
            self.ser = serial.Serial('COM5', self.baudrate, timeout=1)
        except serial.serialutil.SerialException:
            print("Can't open : ", self.portName)
            self.dummyPlug = True
            print("Dummy mode activated")

    def close(self):
        if(self.ser.isOpen()):
            self.ser.close()
        else:
            print(self.portName, " it's already closed")

    def getData(self):
        
        if not self.dummyPlug:
            value = self.ser.readline()  # read line (single value) from the serial port
            decoded_bytes = str(value[0:len(value) - 2].decode("utf-8"))
            #print(decoded_bytes)
            value_chain = decoded_bytes.split(",")
        else:
            value_chain = [float(random.randint(0, 100)) for _ in range(12)]  # generate a random serial chain

        return value_chain

    def isOpen(self):
        return self.ser.isOpen()

    def dummyMode(self):
        return self.dummyPlug
