import sys  # Imports the sys module for system-specific parameters and functions
import logging  # Imports the logging module for logging messages

import pyqtgraph as pg  # Imports the pyqtgraph module for data visualization
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets  # Imports necessary modules from pyqtgraph for GUI elements
from PyQt5.QtWidgets import QPushButton, QSlider, QLabel, QHBoxLayout, QWidget, QVBoxLayout, QDialog  # Imports specific widgets from PyQt5
from PyQt5.QtCore import QThread, pyqtSignal, QObject  # Imports QThread, pyqtSignal, and QObject from PyQt5 for threading

from collections import deque  # Imports deque from collections for efficient appending and popping from both ends

from graphs.graph_acceleration import graph_acceleration  # Imports the graph_acceleration class from the graphs package
from graphs.graph_altitude import graph_altitude  # Imports the graph_altitude class from the graphs package
from graphs.graph_gyro import graph_gyro  # Imports the graph_gyro class from the graphs package
from graphs.graph_pressure import graph_pressure  # Imports the graph_pressure class from the graphs package
from graphs.graph_temperature import graph_temperature  # Imports the graph_temperature class from the graphs package
from graphs.graph_time import graph_time  # Imports the graph_time class from the graphs package
from graphs.graph_ppm import graph_ppm  # Imports the graph_ppm class from the graphs package
from graphs.graph_humidity import graph_humidity  # Imports the graph_humidity class from the graphs package

from dataBase import DataBase  # Imports the DataBase class from the dataBase module
from communication import Communication  # Imports the Communication class from the communication module

import serial  # Imports the serial module for serial communication
import serial.tools.list_ports  # Imports the serial.tools.list_ports module for listing serial ports

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')  # Configures logging

class PortSelectionDialog(QDialog):
    """A dialog for selecting a serial port."""
    def __init__(self):
        super().__init__()  # Initializes the QDialog
        self.setWindowTitle("Select Serial Port")  # Sets the window title
        self.setFixedSize(600, 400)  # Sets a fixed size for the dialog
        self.selected_port = None  # Initializes the selected_port attribute
        main_layout = QVBoxLayout(self)  # Creates a vertical layout for the dialog
        main_layout.setContentsMargins(20, 20, 20, 20)  # Sets margins for the layout

        title_label = QLabel("Available Serial Ports:")  # Creates a label for the title
        title_label.setAlignment(QtCore.Qt.AlignTop)  # Aligns the label to the top
        title_label.setStyleSheet("""QLabel { color: rgb(197, 198, 199); font-size: 20px; margin-bottom: 20px; }""")  # Sets the style for the title label
        main_layout.addWidget(title_label)  # Adds the title label to the main layout

        ports_layout = QVBoxLayout()  # Creates a vertical layout for the port buttons
        main_layout.addLayout(ports_layout)  # Adds the ports layout to the main layout
        main_layout.addStretch(1)  # Adds a stretch to the layout

        available_ports = [port.device for port in serial.tools.list_ports.comports()]  # Lists available serial ports

        if not available_ports:  # If no serial ports are found
            label = QLabel("No serial ports found.")  # Creates a label indicating no ports were found
            label.setAlignment(QtCore.Qt.AlignTop)  # Aligns the label to the top
            label.setStyleSheet("""QLabel { color: rgb(197, 198, 199); font-size: 16px; margin-bottom: 10px; }""")  # Sets the style for the label
            ports_layout.addWidget(label)  # Adds the label to the ports layout
        else:  # If serial ports are found
            for port in available_ports:  # Loops through the available ports
                button = QPushButton(port)  # Creates a button for each port
                button.setStyleSheet("""QPushButton { background-color:rgb(29, 185, 84); color:rgb(0,0,0); font-size:16px; padding: 12px; border-radius: 5px; margin-bottom: 10px; } QPushButton:hover { background-color: rgb(29, 130, 84); }""")  # Sets the style for the button
                button.clicked.connect(lambda checked, p=port: self.select_port(p))  # Connects the button click to the select_port method
                ports_layout.addWidget(button)  # Adds the button to the ports layout

        self.setStyleSheet("""QDialog { background-color: rgb(33, 33, 33); }""")  # Sets the style for the dialog

    def select_port(self, port):
        """Selects a serial port."""
        self.selected_port = port  # Sets the selected_port attribute to the chosen port
        self.accept()  # Accepts the dialog

class DataWorker(QObject):
    """Worker class for emitting signals from the data acquisition thread."""
    data_received = pyqtSignal(list)  # Defines a pyqtSignal for emitting received data

class DataAcquisitionThread(QThread):
    """Thread to handle data acquisition from the serial port."""
    def __init__(self, communication, data_worker):
        super().__init__()  # Initializes the QThread
        self.communication = communication  # Stores the communication object
        self.running = True  # Sets the running flag to True
        self.data_worker = data_worker  # Stores the data worker object

    def run(self):
        while self.running:  # Loops while the running flag is True
            try:
                str_value_chain = self.communication.getData()  # Gets data from the serial port
                value_chain = [float(item) if item else 0.0 for item in str_value_chain]  # Converts the data to floats
                if len(value_chain) >= 12:  # Checks if enough data has been received
                    self.data_worker.data_received.emit(value_chain)  # Emits the data_received signal
            except Exception as e:  # Catches exceptions
                print(f"Error in DataAcquisitionThread: {e}")  # Prints the error message
            self.msleep(50)  # Sleeps for 50 milliseconds

    def stop(self):
        self.running = False  # Sets the running flag to False to stop the loop

class PlottingThread(QThread):
    """Thread to handle graph updates."""
    def __init__(self, gui, data_base):
        super().__init__()  # Initializes the QThread
        self.gui = gui  # Stores the GUI object
        self.data_base = data_base  # Stores the database object
        self.running = True  # Sets the running flag to True

    def run(self):
        """Initializes the GUI, serial communication, and database."""
        # DO NOT CREATE QApplication here. It's created in main()

        # Initialize graph objects
        self.time = graph_time(font=self.gui.font)  # Initializes the time graph
        self.altitude = graph_altitude()  # Initializes the altitude graph
        self.acceleration = graph_acceleration()  # Initializes the acceleration graph
        self.gyro = graph_gyro()  # Initializes the gyro graph
        self.pressure = graph_pressure()  # Initializes the pressure graph
        self.temperature = graph_temperature()  # Initializes the temperature graph
        self.ppm = graph_ppm()  # Initializes the PPM graph
        self.humidity = graph_humidity()  # Initializes the humidity graph

        # Initialize data storage for altitude and time
        self.altitude_data = deque(maxlen=100)  # Initializes a deque for altitude data
        self.time_data = deque(maxlen=100)  # Initializes a deque for time data

        while self.running:  # Loops while the running flag is True
            self.msleep(50)  # Sleeps for 50 milliseconds

    def stop(self):
        self.running = False  # Sets the running flag to False to stop the loop

class FlightMonitoringGUI:
    """Main class for the flight monitoring GUI."""
    def __init__(self, selected_port=None):
        """Initializes the GUI, serial communication, and database."""
        # Graph settings
        pg.setConfigOption('background', (33, 33, 33))  # Sets the background color for pyqtgraph
        pg.setConfigOption('foreground', (197, 198, 199))  # Sets the foreground color for pyqtgraph
        # DO NOT CREATE QApplication here. It's created in main()

        self.view = pg.GraphicsView()  # Creates a GraphicsView object
        self.Layout = pg.GraphicsLayout()  # Creates a GraphicsLayout object
        self.view.setCentralItem(self.Layout)  # Sets the central item of the view to the layout
        self.view.show()  # Shows the view

        if sys.platform.startswith('win'):  # Checks if the platform is Windows
            import os  # Import os here
            directory = os.path.dirname(os.path.abspath(__file__))  # Gets the directory of the current file
            icon_path = os.path.join(directory, "icon.ico")  # Creates the path to the icon file
            self.view.setWindowIcon(QtGui.QIcon(icon_path))  # Sets the window icon
        self.view.setWindowTitle('Flight Monitoring with Servo Control')  # Sets the window title
        self.view.resize(1200, 700)  # Resizes the window

        # Initialize serial communication and database
        self.ser = Communication(port_name=selected_port)  # Initializes the Communication object with the selected port
        self.data_base = DataBase()  # Initializes the DataBase object

        # Set font
        self.font = QtGui.QFont()  # Initializes a QFont object
        self.font.setPixelSize(90)  # Sets the pixel size of the font

        # Define button style
        self.style = "background-color:rgb(29, 185, 84);color:rgb(0,0,0);font-size:14px;"  # Defines the style for the buttons

        # Initialize graph objects
        self.time = graph_time(font=self.font)  # Initializes the time graph
        self.altitude = graph_altitude()  # Initializes the altitude graph
        self.acceleration = graph_acceleration()  # Initializes the acceleration graph
        self.gyro = graph_gyro()  # Initializes the gyro graph
        self.pressure = graph_pressure()  # Initializes the pressure graph
        self.temperature = graph_temperature()  # Initializes the temperature graph
        self.ppm = graph_ppm()  # Initializes the PPM graph
        self.humidity = graph_humidity()  # Initializes the humidity graph

        # Create and start the servo control thread
        self.servo_thread = ServoControlThread()  # Creates a servo control thread
        self.servo_thread.start()  # Starts the servo control thread

        # Initialize data storage for altitude and time
        self.altitude_data = deque(maxlen=100)  # Initializes a deque for altitude data
        self.time_data = deque(maxlen=100)  # Initializes a deque for time data

        # Initialize the user interface
        self.init_ui()  # Initializes the user interface

        # Set up threads and start data acquisition
        self.init_threads()  # Initializes the threads

    def init_ui(self):
        """Initializes the user interface."""
        # Add title at the top
        self.Layout.addLabel("ITS NOT ROCKET SCIENCE", col=1, colspan=11)  # Adds a label to the layout
        self.Layout.nextRow()  # Moves to the next row

        # Add Start/Stop Storage buttons
        proxy1 = QtWidgets.QGraphicsProxyWidget()  # Creates a proxy widget
        self.save_button = QPushButton('Start Storage')  # Creates a button for starting storage
        self.save_button.setStyleSheet(self.style)  # Sets the style for the button
        self.save_button.clicked.connect(self.data_base.start_storage)  # Connects the button click to the start_storage method
        proxy1.setWidget(self.save_button)  # Sets the widget for the proxy
        proxy2 = QtWidgets.QGraphicsProxyWidget()  # Creates a proxy widget
        self.end_save_button = QPushButton('Stop Storage')  # Creates a button for stopping storage
        self.end_save_button.setStyleSheet(self.style)  # Sets the style for the button
        self.end_save_button.clicked.connect(self.data_base.stop_storage)  # Connects the button click to the stop_storage method
        proxy2.setWidget(self.end_save_button)  # Sets the widget for the proxy

        lb = self.Layout.addLayout(colspan=21)  # Adds a layout to the main layout
        lb.addItem(proxy1)  # Adds the first proxy
        lb.nextCol()  # Moves to the next column
        lb.addItem(proxy2)  # Adds the second proxy
        self.Layout.nextRow()  # Moves to the next row

        # Create layout for graphs
        l1 = self.Layout.addLayout(colspan=20, rowspan=4)  # Adds a layout to the main layout

        # Row 1: Altitude, Time
        l11 = l1.addLayout(rowspan=1, border=(83, 83, 83))  # Adds a layout to l1
        l11.addItem(self.altitude)  # Adds the altitude graph to the layout
        l11.addItem(self.time)  # Adds the time graph to the layout
        l1.nextRow()  # Moves to the next row

        # Row 2: Acceleration, Gyro, Pressure, Temperature
        l12 = l1.addLayout(rowspan=1, border=(83, 83, 83))  # Adds a layout to l1
        l12.addItem(self.acceleration)  # Adds the acceleration graph to the layout
        l12.addItem(self.gyro)  # Adds the gyro graph to the layout
        l12.addItem(self.pressure)  # Adds the pressure graph to the layout
        l12.addItem(self.temperature)  # Adds the temperature graph to the layout
        l1.nextRow()  # Moves to the next row

        # Row 3: Humidity, PPM
        l13 = l1.addLayout(rowspan=1, border=(83, 83, 83))  # Adds a layout to l1
        l13.addItem(self.humidity)  # Adds the humidity graph to the layout
        l13.addItem(self.ppm)  # Adds the PPM graph to the layout

        self.Layout.nextRow()  # Moves to the next row

        # Create ServoControl widget and add it to layout
        self.servo_control_widget = ServoControl(self.servo_thread, self.ser)  # Creates a ServoControl widget
        proxy3 = QtWidgets.QGraphicsProxyWidget()  # Creates a proxy widget
        proxy3.setWidget(self.servo_control_widget)  # Sets the widget for the proxy

        l1.nextRow()  # Moves to the next row
        l14 = l1.addLayout(rowspan=1, colspan=20, border=(83, 83, 83))  # Adds a layout to l1
        l14.addItem(proxy3)  # Adds the proxy to the layout

    def init_threads(self):
        """Initialize and start the data acquisition and plotting threads."""
        self.data_worker = DataWorker()  # Creates a DataWorker object
        self.data_acquisition_thread = DataAcquisitionThread(self.ser, self.data_worker)  # Creates a DataAcquisitionThread object
        self.data_worker.data_received.connect(self.update_graphs)  # Connects the data_received signal to the update_graphs method
        self.data_acquisition_thread.start()  # Starts the data acquisition thread

    def update_graphs(self, value_chain):
        """Update the graphs with new data. This runs in the *main* thread."""
        if len(value_chain) < 12:  # Checks if the length of the value chain is less than 12
            print("Incomplete data received.")  # Handle incomplete data
            return

        try:
            # Extract data
            altitude = value_chain[4]  # Extracts altitude from value chain
            time = value_chain[0]  # Extracts time from value chain
            acceleration = value_chain[9:12]  # Slice for acceleration values
            gyro = value_chain[6:9]  # Slice for gyro values
            pressure = value_chain[3]  # Extracts pressure from value chain
            temperature = value_chain[2]  # Extracts temperature from value chain
            ppm = value_chain[5]  # Extracts PPM from value chain
            humidity = value_chain[1]  # Extracts humidity from value chain

            # Update graphs
            self.altitude.update(altitude)  # Updates the altitude graph
            self.time.update(time)  # Updates the time graph
            self.acceleration.update(*acceleration)  # Unpack the slice
            self.gyro.update(*gyro)  # Unpack the slice
            self.pressure.update(pressure)  # Updates the pressure graph
            self.temperature.update(temperature)  # Updates the temperature graph
            self.ppm.update(ppm)  # Updates the PPM graph
            self.humidity.update(humidity)  # Updates the humidity graph

            # Save data to the database
            self.data_base.store_data(value_chain)  # Stores the data in the database

        except (IndexError, ValueError) as e:  # Catch specific exceptions
            print(f"Error updating graphs: {e}")  # Prints error message

    def run(self):
        """Runs the application event loop."""
        try:
            if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
                sys.exit(self.app.exec_())  # Exits the application
        finally:
            self.cleanup()  # Calls the cleanup method

    def cleanup(self):
        """Stop the threads when the GUI is closed."""
        self.data_acquisition_thread.stop()  # Stops the data acquisition thread
        self.servo_thread.stop()  # Stop Servo Thread as well
        self.data_acquisition_thread.wait()  # Waits for the data acquisition thread to finish
        self.servo_thread.wait()  # Waits for the servo thread to finish

# Servo Control Thread for Independent Execution
class ServoControlThread(QThread):
    servo_signal = pyqtSignal(int, int)  # Signal to send servo data (servo ID and angle)

    def __init__(self):
        super().__init__()  # Initializes the QThread
        self.running = True  # Sets the running flag to True
        self.queue = []  # Queue to store commands

    def run(self):
        while self.running:  # Loops while the running flag is True
            if self.queue:  # Checks if the queue is not empty
                servo_id, angle = self.queue.pop(0)  # Get the next command in the queue
                self.servo_signal.emit(servo_id, angle)  # Emit the signal with servo data
                self.msleep(50)  # Sleep for a short time to avoid high CPU usage

    def add_command(self, servo_id, angle):
        """Add a command to the queue."""
        self.queue.append((servo_id, angle))  # Appends a servo command to the queue

    def stop(self):
        """Stop the thread."""
        self.running = False  # Sets the running flag to False to stop the loop

# Servo Control Widget for User Interaction with Sliders
class ServoControl(QWidget):
    def __init__(self, servo_thread: ServoControlThread, ser: Communication):
        super().__init__()  # Initializes the QWidget
        self.servo_thread = servo_thread  # Reference to the servo control thread
        self.initUI()  # Initializes the UI
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
        layout = QHBoxLayout()  # Creates a horizontal layout

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
        self.label_servo1 = QLabel("Servo 1 Angle: 0°")  # Creates a label for Servo 1
        self.slider_servo1 = QSlider(QtCore.Qt.Horizontal)  # Creates a horizontal slider for Servo 1
        self.slider_servo1.setMinimum(-90)  # Sets the minimum value of the slider
        self.slider_servo1.setMaximum(90)  # Sets the maximum value of the slider
        self.slider_servo1.setValue(0)  # Sets the initial value of the slider
        self.slider_servo1.valueChanged.connect(self.update_servo1)  # Connects the valueChanged signal to the update_servo1 method

        # Slider for Servo 2
        self.label_servo2 = QLabel("Servo 2 Angle: 0°")  # Creates a label for Servo 2
        self.slider_servo2 = QSlider(QtCore.Qt.Horizontal)  # Creates a horizontal slider for Servo 2
        self.slider_servo2.setMinimum(-90)  # Sets the minimum value of the slider
        self.slider_servo2.setMaximum(90)  # Sets the maximum value of the slider
        self.slider_servo2.setValue(0)  # Sets the initial value of the slider
        self.slider_servo2.valueChanged.connect(self.update_servo2)  # Connects the valueChanged signal to the update_servo2 method

        # Add widgets to layout with spacing between sliders
        layout.addWidget(self.label_servo1)  # Adds the label to the layout
        layout.addWidget(self.slider_servo1)  # Adds the slider to the layout
        layout.addSpacing(20)  # Adds spacing to the layout
        layout.addWidget(self.label_servo2)  # Adds the label to the layout
        layout.addWidget(self.slider_servo2)  # Adds the slider to the layout
        self.setLayout(layout)  # Sets the layout for the widget

    def update_servo1(self, value):
        """Update Servo 1 angle."""
        self.label_servo1.setText(f"Servo 1 Angle: {value}°")  # Sets the text of the label
        self.servo1_value = value
        self.servo1_timer.start(1000)  # Restart the timer

    def update_servo2(self, value):
        """Update Servo 2 angle."""
        self.label_servo2.setText(f"Servo 2 Angle: {value}°")  # Sets the text of the label
        self.servo2_value = value
        self.servo2_timer.start(1000)  # Restart the timer

    def send_servo1_command(self):
        """Send the current servo 1 value to the thread if it has changed."""
        if self.servo1_value != self.last_servo1_value:
            self.serialSend()  # Sending over to pico
            self.last_servo1_value = self.servo1_value

    def send_servo2_command(self):
        """Send the current servo 2 value to the thread if it has changed."""
        if self.servo2_value != self.last_servo2_value:
            self.serialSend()  # Sending over to pico
            self.last_servo2_value = self.servo2_value

    def serialSend(self):
        try:
            message = f"{self.servo1_value},{self.servo2_value}"  # Create the message
            self.ser.serial_send(message)  # Send the message
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    # Create the QApplication instance *once* at the beginning.
    app = QtWidgets.QApplication(sys.argv)  # Creates a QApplication object

    # Show the port selection dialog
    port_dialog = PortSelectionDialog()  # Creates a PortSelectionDialog object
    result = port_dialog.exec_()  # Execute the dialog and get the result

    if result == QDialog.Accepted:  # Checks if the dialog was accepted
        selected_port = port_dialog.selected_port  # Gets the selected port

        # Initialize and run the main GUI *only* if a port was selected.
        gui = FlightMonitoringGUI(selected_port)  # Pass the selected port
        gui.app = app  # VERY IMPORTANT
        gui.run()  # Run the GUI
    else:
        print("No serial port selected. Exiting.")  # Prints message
        sys.exit(app.exec_())  # Ensure the application exits cleanly