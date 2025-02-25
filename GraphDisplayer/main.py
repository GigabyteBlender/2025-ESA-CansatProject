import sys
import logging
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import QPushButton, QSlider, QLabel, QHBoxLayout, QWidget, QVBoxLayout, QDialog
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from collections import deque
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
    def __init__(self, communication, data_worker):
        super().__init__()
        self.communication = communication
        self.running = True
        self.data_worker = data_worker

    def run(self):
        while self.running:
            try:
                str_value_chain = self.communication.getData()
                value_chain = [float(item) if item else 0.0 for item in str_value_chain]
                if len(value_chain) >= 12:
                    self.data_worker.data_received.emit(value_chain)
            except Exception as e:
                print(f"Error in DataAcquisitionThread: {e}")
            self.msleep(50)

    def stop(self):
        self.running = False

class PlottingThread(QThread):
    """Thread to handle graph updates."""
    def __init__(self, gui, data_base):
        super().__init__()
        self.gui = gui
        self.data_base = data_base
        self.running = True

    def run(self):
        """Initializes the GUI, serial communication, and database."""
        # DO NOT CREATE QApplication here.  It's created in main()
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

        # DO NOT CREATE QApplication here.  It's created in main()

        self.view = pg.GraphicsView()
        self.Layout = pg.GraphicsLayout()
        self.view.setCentralItem(self.Layout)
        self.view.show()

        if sys.platform.startswith('win'):
            import os # Import os here
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

        # Create and start the servo control thread
        self.servo_thread = ServoControlThread()
        self.servo_thread.start()

        # Initialize data storage for altitude and time
        self.altitude_data = deque(maxlen=100)
        self.time_data = deque(maxlen=100)

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

        lb = self.Layout.addLayout(colspan=21)
        lb.addItem(proxy1)
        lb.nextCol()
        lb.addItem(proxy2)
        self.Layout.nextRow()

        # Create layout for graphs
        l1 = self.Layout.addLayout(colspan=20, rowspan=4)

        # Row 1: Altitude, Time
        l11 = l1.addLayout(rowspan=1, border=(83, 83, 83))
        l11.addItem(self.altitude)
        l11.addItem(self.time)
        l1.nextRow()

        # Row 2: Acceleration, Gyro, Pressure, Temperature
        l12 = l1.addLayout(rowspan=1, border=(83, 83, 83))
        l12.addItem(self.acceleration)
        l12.addItem(self.gyro)
        l12.addItem(self.pressure)
        l12.addItem(self.temperature)
        l1.nextRow()

        # Row 3: Humidity, PPM
        l13 = l1.addLayout(rowspan=1, border=(83, 83, 83))
        l13.addItem(self.humidity)
        l13.addItem(self.ppm)
        self.Layout.nextRow()

        # Create ServoControl widget and add it to layout
        self.servo_control_widget = ServoControl(self.servo_thread, self.ser)
        proxy3 = QtWidgets.QGraphicsProxyWidget()
        proxy3.setWidget(self.servo_control_widget)
        l1.nextRow()
        l14 = l1.addLayout(rowspan=1, colspan=20, border=(83, 83, 83))
        l14.addItem(proxy3)

    def init_threads(self):
        """Initialize and start the data acquisition and plotting threads."""
        self.data_worker = DataWorker()
        self.data_acquisition_thread = DataAcquisitionThread(self.ser, self.data_worker)

        self.data_worker.data_received.connect(self.update_graphs)

        self.data_acquisition_thread.start()

    def update_graphs(self, value_chain):
        """Update the graphs with new data.  This runs in the *main* thread."""
        if len(value_chain) < 12:
            print("Incomplete data received.")  # Handle incomplete data
            return

        try:
            # Extract data
            altitude = value_chain[4]
            time = value_chain[0]
            acceleration = value_chain[9:12]  # Slice for acceleration values
            gyro = value_chain[6:9]  # Slice for gyro values
            pressure = value_chain[3]
            temperature = value_chain[2]
            ppm = value_chain[5]
            humidity = value_chain[1]

            # Update graphs
            self.altitude.update(altitude)
            self.time.update(time)
            self.acceleration.update(*acceleration)  # Unpack the slice
            self.gyro.update(*gyro)  # Unpack the slice
            self.pressure.update(pressure)
            self.temperature.update(temperature)
            self.ppm.update(ppm)
            self.humidity.update(humidity)

            # Save data to the database
            self.data_base.store_data(value_chain)

        except (IndexError, ValueError) as e:  # Catch specific exceptions
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
        self.servo_thread.stop() #Stop Servo Thread as well
        self.data_acquisition_thread.wait()
        self.servo_thread.wait()

# Servo Control Thread for Independent Execution
class ServoControlThread(QThread):
    servo_signal = pyqtSignal(int, int) # Signal to send servo data (servo ID and angle)
    def __init__(self):
        super().__init__()
        self.running = True
        self.queue = [] # Queue to store commands

    def run(self):
        while self.running:
            if self.queue:
                servo_id, angle = self.queue.pop(0) # Get the next command in the queue
                self.servo_signal.emit(servo_id, angle) # Emit the signal with servo data
                self.msleep(50) # Sleep for a short time to avoid high CPU usage

    def add_command(self, servo_id, angle):
        """Add a command to the queue."""
        self.queue.append((servo_id, angle))

    def stop(self):
        """Stop the thread."""
        self.running = False

# Servo Control Widget for User Interaction with Sliders
class ServoControl(QWidget):
    def __init__(self, servo_thread: ServoControlThread, ser: Communication):
        super().__init__()
        self.servo_thread = servo_thread # Reference to the servo control thread
        self.initUI()
        self.servo1_value = 0
        self.servo2_value = 0
        self.last_servo1_value = 0
        self.last_servo2_value = 0
        self.servo1_timer = QtCore.QTimer()
        self.servo2_timer = QtCore.QTimer()
        self.ser = ser
        self.servo1_timer.setSingleShot(True)
        self.servo2_timer.setSingleShot(True)
        self.servo1_timer.timeout.connect(self.send_servo1_command)
        self.servo2_timer.timeout.connect(self.send_servo2_command)

    def initUI(self):
        layout = QHBoxLayout()

        # Set background color and styling for the widget and labels
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

        # Slider for Servo 1
        self.label_servo1 = QLabel("Servo 1 Angle: 0°")
        self.slider_servo1 = QSlider(QtCore.Qt.Horizontal)
        self.slider_servo1.setMinimum(-90)
        self.slider_servo1.setMaximum(90)
        self.slider_servo1.setValue(0)
        self.slider_servo1.valueChanged.connect(self.update_servo1)

        # Slider for Servo 2
        self.label_servo2 = QLabel("Servo 2 Angle: 0°")
        self.slider_servo2 = QSlider(QtCore.Qt.Horizontal)
        self.slider_servo2.setMinimum(-90)
        self.slider_servo2.setMaximum(90)
        self.slider_servo2.setValue(0)
        self.slider_servo2.valueChanged.connect(self.update_servo2)

        # Add widgets to layout with spacing between sliders
        layout.addWidget(self.label_servo1)
        layout.addWidget(self.slider_servo1)
        layout.addSpacing(20)
        layout.addWidget(self.label_servo2)
        layout.addWidget(self.slider_servo2)
        self.setLayout(layout)

    def update_servo1(self, value):
        """Update Servo 1 angle."""
        self.label_servo1.setText(f"Servo 1 Angle: {value}°")
        self.servo1_value = value
        self.servo1_timer.start(1000) # Restart the timer

    def update_servo2(self, value):
        """Update Servo 2 angle."""
        self.label_servo2.setText(f"Servo 2 Angle: {value}°")
        self.servo2_value = value
        self.servo2_timer.start(1000) # Restart the timer

    def send_servo1_command(self):
        """Send the current servo 1 value to the thread if it has changed."""
        if self.servo1_value != self.last_servo1_value:
            self.serialSend() #Sending over to pico
            self.last_servo1_value = self.servo1_value

    def send_servo2_command(self):
        """Send the current servo 2 value to the thread if it has changed."""
        if self.servo2_value != self.last_servo2_value:
            self.serialSend() #Sending over to pico
            self.last_servo2_value = self.servo2_value

    def serialSend(self):
        try:
            message = f"{self.servo1_value},{self.servo2_value}" # Create the message
            self.ser.serial_send(message) # Send the message
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    # Create the QApplication instance *once* at the beginning.
    app = QtWidgets.QApplication(sys.argv)

    # Show the port selection dialog
    port_dialog = PortSelectionDialog()
    result = port_dialog.exec_() # Execute the dialog and get the result

    if result == QDialog.Accepted:
        selected_port = port_dialog.selected_port
        # Initialize and run the main GUI *only* if a port was selected.
        gui = FlightMonitoringGUI(selected_port) # Pass the selected port
        gui.app = app #VERY IMPORTANT
        gui.run()  # Run the GUI
    else:
        print("No serial port selected. Exiting.")

    sys.exit(app.exec_()) # Ensure the application exits cleanly