import sys
import logging
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import QPushButton, QSlider, QLabel, QHBoxLayout, QWidget, QVBoxLayout, QDialog
from PyQt5.QtCore import QThread, pyqtSignal, QObject, QTimer
from collections import deque
import numpy as np
from graphs.graph_acceleration import graph_acceleration
from graphs.graph_altitude import graph_altitude
from graphs.graph_gyro import graph_gyro
from graphs.graph_pressure import graph_pressure
from graphs.graph_temperature import graph_temperature
from graphs.graph_time import graph_time
from graphs.graph_ppm import graph_ppm
from graphs.graph_humidity import graph_humidity
from dataBase import DataBase
from communication import Communication
import serial
import serial.tools.list_ports 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PortSelectionDialog(QDialog):
    """A dialog for selecting a serial port."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Serial Port")
        self.setFixedSize(600, 400)
        self.selected_port = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Available Serial Ports:")
        title_label.setAlignment(QtCore.Qt.AlignTop)
        title_label.setStyleSheet("""QLabel { color: rgb(197, 198, 199); font-size: 20px; margin-bottom: 20px; }""")
        main_layout.addWidget(title_label)

        ports_layout = QVBoxLayout()
        main_layout.addLayout(ports_layout)
        main_layout.addStretch(1)

        available_ports = [port.device for port in serial.tools.list_ports.comports()]

        if not available_ports:
            label = QLabel("No serial ports found.")
            label.setAlignment(QtCore.Qt.AlignTop)
            label.setStyleSheet("""QLabel { color: rgb(197, 198, 199); font-size: 16px; margin-bottom: 10px; }""")
            ports_layout.addWidget(label)
        else:
            for port in available_ports:
                button = QPushButton(port)
                button.setStyleSheet("""QPushButton { background-color:rgb(29, 185, 84); color:rgb(0,0,0); font-size:16px; padding: 12px; border-radius: 5px; margin-bottom: 10px; } QPushButton:hover { background-color: rgb(29, 130, 84); }""")
                button.clicked.connect(lambda checked, p=port: self.select_port(p))
                ports_layout.addWidget(button)

        self.setStyleSheet("""QDialog { background-color: rgb(33, 33, 33); }""")

    def select_port(self, port):
        """Selects a serial port."""
        self.selected_port = port
        self.accept()

class DataWorker(QObject):
    """Worker class for emitting signals from the data acquisition thread."""

    data_received = pyqtSignal(list)

class DataAcquisitionThread(QThread):
    """Thread to handle data acquisition from the serial port."""

    def __init__(self, communication: Communication, data_worker: DataWorker):
        super().__init__()
        self.communication = communication
        self.running = True
        self.data_worker = data_worker

    def run(self):
        while self.running:
            try:
                str_value_chain = self.communication.getData()
                # Use numpy for faster conversion
                try:
                    value_chain = np.array(str_value_chain, dtype=float)
                except ValueError as e:
                    print(f"ValueError during conversion: {e}, Data: {str_value_chain}")
                    continue  # Skip this iteration if conversion fails

                if value_chain.size >= 12:
                    self.data_worker.data_received.emit(value_chain.tolist())
            except Exception as e:
                print(f"Error in DataAcquisitionThread: {e}")

            self.msleep(5)  # Reduced sleep time (adjustable)

    def stop(self):
        self.running = False

class PlottingThread(QThread):
    """Thread to handle graph updates."""

    def __init__(self, gui, data_base):
        super().__init__()
        self.gui = gui
        self.data_base = data_base
        self.running = True

        # Initialize graph objects
        self.time = graph_time(font=self.gui.font)
        self.altitude = graph_altitude()
        self.acceleration = graph_acceleration()
        self.gyro = graph_gyro()
        self.pressure = graph_pressure()
        self.temperature = graph_temperature()
        self.ppm = graph_ppm()
        self.humidity = graph_humidity()

        # Initialize data storage for altitude and time
        self.altitude_data = deque(maxlen=100)
        self.time_data = deque(maxlen=100)

    def run(self):
        while self.running:
            self.msleep(50)

    def stop(self):
        self.running = False

class FlightMonitoringGUI:
    """Main class for the flight monitoring GUI."""

    def __init__(self, selected_port=None):
        """Initializes the GUI, serial communication, and database."""
        # Graph settings
        pg.setConfigOption('background', (33, 33, 33))
        pg.setConfigOption('foreground', (197, 198, 199))

        self.view = pg.GraphicsView()
        self.Layout = pg.GraphicsLayout()
        self.view.setCentralItem(self.Layout)
        self.view.show()

        if sys.platform.startswith('win'):
            import os
            directory = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(directory, "icon.ico")
            self.view.setWindowIcon(QtGui.QIcon(icon_path))

        self.view.setWindowTitle('Flight Monitoring with Servo Control')
        self.view.resize(1200, 700)

        # Initialize serial communication and database
        self.ser = Communication(port_name=selected_port)
        self.data_base = DataBase()

        # Set font
        self.font = QtGui.QFont()
        self.font.setPixelSize(90)

        # Define button style
        self.style = "background-color:rgb(29, 185, 84);color:rgb(0,0,0);font-size:14px;"

        # Initialize graph objects
        self.time = graph_time(font=self.font)
        self.altitude = graph_altitude()
        self.acceleration = graph_acceleration()
        self.gyro = graph_gyro()
        self.pressure = graph_pressure()
        self.temperature = graph_temperature()
        self.ppm = graph_ppm()
        self.humidity = graph_humidity()

        # Initialize data storage for altitude and time
        self.altitude_data = deque(maxlen=100)
        self.time_data = deque(maxlen=100)

        # Create and start the servo control thread
        self.servo_thread = ServoControlThread(self.ser)  # Pass communication object
        self.servo_thread.start()

        # Initialize the user interface
        self.init_ui()

        # Set up threads and start data acquisition
        self.init_threads()

    def init_ui(self):
        """Initializes the user interface."""
        # Add title at the top
        self.Layout.addLabel("ITS NOT ROCKET SCIENCE", col=1, colspan=11)
        self.Layout.nextRow()

        # Add Start/Stop Storage buttons
        proxy1 = QtWidgets.QGraphicsProxyWidget()
        self.save_button = QPushButton('Start Storage')
        self.save_button.setStyleSheet(self.style)
        self.save_button.clicked.connect(self.data_base.start_storage)
        proxy1.setWidget(self.save_button)

        proxy2 = QtWidgets.QGraphicsProxyWidget()
        self.end_save_button = QPushButton('Stop Storage')
        self.end_save_button.setStyleSheet(self.style)
        self.end_save_button.clicked.connect(self.data_base.stop_storage)
        proxy2.setWidget(self.end_save_button)
        
        proxy3 = QtWidgets.QGraphicsProxyWidget()
        self.start_stop_button = QPushButton('Start/Stop Cansat')
        self.start_stop_button.setStyleSheet(self.style)
        self.start_stop_button.clicked.connect(lambda: self.ser.serial_send("start_stop"))
        proxy3.setWidget(self.start_stop_button)

        lb = self.Layout.addLayout(colspan=21)
        lb.addItem(proxy1)
        lb.nextCol()
        lb.addItem(proxy2)
        lb.nextCol()
        lb.addItem(proxy3)
        self.Layout.nextRow()

        # Create layout for graphs
        l1 = self.Layout.addLayout(colspan=20, rowspan=4)

        # Row 1: Altitude, Time
        l11 = l1.addLayout(rowspan=1, border=(83, 83, 83))
        l11.addItem(self.altitude)
        l11.addItem(self.pressure)
        l11.addItem(self.time)
        self.time.setFixedHeight(200)
        self.time.setFixedWidth(300)
        l1.nextRow()

        # Row 2: Acceleration, Gyro, Pressure, Temperature
        l12 = l1.addLayout(rowspan=1, border=(83, 83, 83))
        l12.addItem(self.acceleration)
        self.acceleration.setFixedHeight(170)
        self.acceleration.setFixedWidth(400)
        l12.addItem(self.gyro)
        self.gyro.setFixedHeight(170)
        self.gyro.setFixedWidth(400)
        l12.addItem(self.temperature)
        l1.nextRow()

        # Row 3: Humidity, PPM
        l13 = l1.addLayout(rowspan=1, border=(83, 83, 83))
        l13.addItem(self.humidity)
        l13.addItem(self.ppm)
        self.Layout.nextRow()

        # Create ServoControl widget and add it to layout
        self.servo_control_widget = ServoControl(self.servo_thread)  # Remove communication object
        proxy3 = QtWidgets.QGraphicsProxyWidget()
        proxy3.setWidget(self.servo_control_widget)
        l1.nextRow()
        l14 = l1.addLayout(rowspan=1, colspan=20, border=(83, 83, 83))
        l14.addItem(proxy3)

    def init_threads(self):
        """Initialize and start the data acquisition and plotting threads."""
        self.data_worker = DataWorker()
        self.data_acquisition_thread = DataAcquisitionThread(self.ser, self.data_worker)
        self.plotting_thread = PlottingThread(self, self.data_base)

        self.data_worker.data_received.connect(self.update_graphs)

        self.data_acquisition_thread.start()
        self.plotting_thread.start()

    def update_graphs(self, value_chain):
        """Update the graphs with new data. This runs in the *main* thread."""
        if len(value_chain) < 12:
            print("Incomplete data received.")
            return

        try:
            # Extract data
            altitude = value_chain[4]
            time = value_chain[0]
            acceleration = value_chain[9:12]
            gyro = value_chain[6:9]
            pressure = value_chain[3]
            temperature = value_chain[2]
            ppm = value_chain[5]
            humidity = value_chain[1]

            # Update graphs
            self.altitude.update(altitude)
            self.time.update(time)
            self.acceleration.update(*acceleration)
            self.gyro.update(*gyro)
            self.pressure.update(pressure)
            self.temperature.update(temperature)
            self.ppm.update(ppm)
            self.humidity.update(humidity)

            # Save data to the database
            self.data_base.store_data(value_chain)

        except (IndexError, ValueError) as e:
            print(f"Error updating graphs: {e}")

    def run(self):
        """Runs the application event loop."""
        try:
            if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
                sys.exit(self.app.exec_())
        finally:
            self.cleanup()

    def cleanup(self):
        """Stop the threads when the GUI is closed."""
        self.data_acquisition_thread.stop()
        self.plotting_thread.stop()
        self.servo_thread.stop()

        self.data_acquisition_thread.wait()
        self.plotting_thread.wait()
        self.servo_thread.wait()

# Servo Control Thread for Independent Execution
class ServoControlThread(QThread):
    servo_signal = pyqtSignal(int, int)  # Signal to send servo data (servo ID and angle)

    def __init__(self, serial_communication: Communication):  # Add serial communication object
        super().__init__()
        self.running = True 
        self.queue = []  # Queue to store servo commands
        self.serial_communication = serial_communication  # Store communication object

    def run(self):
        while self.running:
            if self.queue:
                servo1, servo2 = self.queue.pop(0)
                # Implement Servo Control Logic Here
                data = f"{servo1},{servo2}"
                self.serial_communication.serial_send(data)  # Use communication object to send data
                self.msleep(50)  # Rate Limiting
            else:
                self.msleep(10)

    def add_command(self, angle1, angle2):
        self.queue.append((angle1, angle2))

    def stop(self):
        self.running = False

class ServoControl(QWidget):
    def __init__(self, servo_thread: ServoControlThread):  # Remove communication object
        super().__init__()
        self.servo_thread = servo_thread
        self.initUI()
        self.servo1_timer = QTimer()
        self.servo1_timer.timeout.connect(self.send_servo1_command)
        self.servo2_timer = QTimer()
        self.servo2_timer.timeout.connect(self.send_servo2_command)

        self.servo1_current_value = 0  # Default angle
        self.servo2_current_value = 0  # Default angle

        self.servo1_is_moving = False
        self.servo2_is_moving = False

    def initUI(self):
        main_layout = QVBoxLayout()

        self.setStyleSheet("""
            QWidget {
            background-color: rgb(33, 33, 33);
            }

            QLabel {
            background-color: rgb(33, 33, 33);
            color: rgb(197, 198, 199);
            font-size: 14px;
            }

            QSlider::groove:horizontal {
            height: 3px;
            margin: 0px;
            background-color: rgb(52, 59, 72);
            }

            QSlider::handle:horizontal {
            background-color: rgb(29, 185, 84);
            height: 10px;
            width: 10px;
            margin: -10px 0;
            border-radius: 0px;
            padding: -10px 0px;
            }

            QSlider::handle:horizontal:hover {
            background-color: rgb(29, 130, 84);
            }
        """)

        # Servo 1 Control
        servo1_layout = QHBoxLayout()
        servo1_label = QLabel("Servo 1 Angle:")
        self.servo1_slider = QSlider(QtCore.Qt.Horizontal)
        self.servo1_slider.setRange(-90, 90)
        self.servo1_slider.setValue(0)  # Default angle
        self.servo1_value_label = QLabel(str(self.servo1_slider.value()))
        self.servo1_slider.valueChanged.connect(lambda value: self.slider1_moved(value))
        self.servo1_value_label.valueChanged = lambda value: self.servo1_value_label.setText(str(value))

        servo1_layout.addWidget(servo1_label)
        servo1_layout.addWidget(self.servo1_slider)
        servo1_layout.addWidget(self.servo1_value_label)
        main_layout.addLayout(servo1_layout)

        # Servo 2 Control (Example)
        servo2_layout = QHBoxLayout()
        servo2_label = QLabel("Servo 2 Angle:")
        self.servo2_slider = QSlider(QtCore.Qt.Horizontal)
        self.servo2_slider.setRange(-90, 90)
        self.servo2_slider.setValue(0)  # Default angle
        self.servo2_value_label = QLabel(str(self.servo2_slider.value()))
        self.servo2_slider.valueChanged.connect(lambda value: self.slider2_moved(value))
        self.servo2_value_label.valueChanged = lambda value: self.servo2_value_label.setText(str(value))

        servo2_layout.addWidget(servo2_label)
        servo2_layout.addWidget(self.servo2_slider)
        servo2_layout.addWidget(self.servo2_value_label)
        main_layout.addLayout(servo2_layout)

        self.setLayout(main_layout)

    def slider1_moved(self, value):
        """Called when the slider is moved."""
        self.servo1_current_value = value
        self.servo1_value_label.setText(str(value))
        self.servo1_timer.start(500)  # Adjust delay as needed
        self.servo1_is_moving = True

    def slider2_moved(self, value):
        """Called when the slider is moved."""
        self.servo2_current_value = value
        self.servo2_value_label.setText(str(value))
        self.servo2_timer.start(500)  # Adjust delay as needed
        self.servo2_is_moving = True

    def send_servo1_command(self):
        """Sends the servo command if the slider hasn't moved for a while."""
        if self.servo1_is_moving:
            self.servo1_is_moving = False
            self.update_servo_angle()
            self.servo1_timer.stop()

    def send_servo2_command(self):
        """Sends the servo command if the slider hasn't moved for a while."""
        if self.servo2_is_moving:
            self.servo2_is_moving = False
            self.update_servo_angle()
            self.servo2_timer.stop()

    def update_servo_angle(self):
        """Update servo angle using the ServoControlThread."""
        self.servo_thread.add_command(self.servo1_current_value, self.servo2_current_value)

def main():
    """Main function to run the flight monitoring application."""
    app = QtWidgets.QApplication(sys.argv)
    dialog = PortSelectionDialog()
    if dialog.exec_() == QDialog.Accepted:
        selected_port = dialog.selected_port
    else:
        print("No port selected. Exiting.")
        return

    gui = FlightMonitoringGUI(selected_port)
    gui.app = app
    gui.run()

if __name__ == '__main__':
    main()