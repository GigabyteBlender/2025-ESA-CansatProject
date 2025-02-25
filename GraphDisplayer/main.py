import sys
import logging
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import QPushButton, QSlider, QLabel, QHBoxLayout, QWidget, QVBoxLayout, QDialog
from PyQt5.QtCore import QThread, pyqtSignal
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

    """A dialog for selecting a serial port, styled to match the main GUI."""

    def __init__(self):
        """Initializes the port selection dialog."""
        super().__init__()

        self.setWindowTitle("Select Serial Port")
        self.setFixedSize(600, 400)  # Adjusted size, can be tweaked
        self.selected_port = None

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20) # Add some padding

        # Title Label
        title_label = QLabel("Available Serial Ports:")
        title_label.setAlignment(QtCore.Qt.AlignTop)
        title_label.setStyleSheet("""
            QLabel {
                color: rgb(197, 198, 199);
                font-size: 20px;
                margin-bottom: 20px;
            }
        """)
        main_layout.addWidget(title_label)

        # Available ports layout
        ports_layout = QVBoxLayout()
        main_layout.addLayout(ports_layout)
        main_layout.addStretch(1)  # Add some space at the bottom

        # List available serial ports
        available_ports = [port.device for port in serial.tools.list_ports.comports()]

        if not available_ports:
            label = QLabel("No serial ports found.")
            label.setAlignment(QtCore.Qt.AlignTop)  # Center the label
            label.setStyleSheet("""
                QLabel {
                    color: rgb(197, 198, 199);
                    font-size: 16px;
                    margin-bottom: 10px;
                }
            """)
            ports_layout.addWidget(label)
        else:
            self.port_buttons = []
            for port in available_ports:
                button = QPushButton(port)
                button.setStyleSheet("""
                    QPushButton {
                        background-color:rgb(29, 185, 84);
                        color:rgb(0,0,0);
                        font-size:16px;
                        padding: 12px;
                        border-radius: 5px;
                        margin-bottom: 10px;
                    }
                    QPushButton:hover {
                        background-color: rgb(29, 130, 84);
                    }
                """)
                button.clicked.connect(lambda checked, p=port: self.select_port(p))
                ports_layout.addWidget(button)
                self.port_buttons.append(button)

        # Apply dark theme styling to the dialog
        self.setStyleSheet("""
            QDialog {
                background-color: rgb(33, 33, 33);
            }
        """)


    def select_port(self, port):
        """Selects a serial port and closes the dialog."""
        self.selected_port = port
        self.accept()  # Close the dialog with acceptance status

class FlightMonitoringGUI:
    """Main class for the flight monitoring GUI."""

    def __init__(self, selected_port=None):
        """Initializes the GUI, serial communication, and database."""
        # Graph settings
        pg.setConfigOption('background', (33, 33, 33))
        pg.setConfigOption('foreground', (197, 198, 199))

        # Create application and main window
        if sys.platform.startswith('win'):
            self.app = QtWidgets.QApplication(sys.argv + ['-platform', 'windows:darkmode=1'])
        else:
            self.app = QtWidgets.QApplication(sys.argv)

        self.view = pg.GraphicsView()
        self.Layout = pg.GraphicsLayout()
        self.view.setCentralItem(self.Layout)
        self.view.show()

        if sys.platform.startswith('win'):
            import os  # Import os here
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
        self.start_data_acquisition()

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

    def start_data_acquisition(self):
        """Set up a QTimer for periodic updates."""
        if self.ser.isOpen() or self.ser.dummyMode():
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self.update)
            self.timer.start(500)  # Update every 500ms

    def update(self):
        try:
            # Get data from the serial communication
            str_value_chain = self.ser.getData()
            value_chain = [float(item) if item else 0.0 for item in str_value_chain]
            if len(value_chain) >= 12:
                # Update graphs with the latest data
                self.altitude.update(value_chain[4])
                self.time.update(value_chain[0])
                self.acceleration.update(value_chain[9], value_chain[10], value_chain[11])
                self.gyro.update(value_chain[6], value_chain[7], value_chain[8])
                self.pressure.update(value_chain[3])
                self.temperature.update(value_chain[2])
                self.ppm.update(value_chain[5])
                self.humidity.update(value_chain[1])

                # Save data to the database
                self.data_base.store_data(value_chain)

        except IndexError as e:
            print(f"Starting, please wait a moment: {e}")
        except ValueError as e:
            print(f"Invalid data received: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def run(self):
        try:
            if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
                sys.exit(self.app.exec_())
        finally:
            self.cleanup()

    def cleanup(self):
        # Stop the servo control thread
        self.servo_thread.stop()

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
    # Before starting the main application, show the port selection dialog
    app = QtWidgets.QApplication(sys.argv)
    port_dialog = PortSelectionDialog()
    result = port_dialog.exec_()  # Execute the dialog and get the result

    if result == QDialog.Accepted:
        selected_port = port_dialog.selected_port
        gui = FlightMonitoringGUI(selected_port)  # Pass the selected port
        gui.run()
    else:
        print("No serial port selected. Exiting.")
        sys.exit()