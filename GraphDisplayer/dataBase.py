import os

class data_base():
    def __init__(self):
        self.state = False
        self.create_file()

    def create_file(self):
        directory = os.path.dirname(os.path.abspath(__file__))
        self.file_path = os.path.join(directory, "flight_data.txt")
        file = open(self.file_path, "w+")
        file.write('Time, Humidity, Temperature, Pressure, Altitude, PPM, GyroX, GyroY, GyroZ, AccX, AccY, AccZ\n')
        file.close()

    def guardar(self, data):
        data = ', '.join(map(str, data))
        if self.state:
            with open(self.file_path, "a") as f:
                f.write(str(data) + '\n')


    def start(self):
        self.state = True
        print('starting storage in csv')

    def stop(self):
        self.state = False
        print('stopping storage in csv')
