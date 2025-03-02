import sys  # Import the sys module for system-specific parameters and functions
import logging  # Import the logging module for logging messages
import pyqtgraph as pg  # Import the pyqtgraph library for plotting
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets  # Import QtGui, QtCore, and QtWidgets from pyqtgraph.Qt
from PyQt5.QtWidgets import QPushButton, QSlider, QLabel, QHBoxLayout, QWidget, QVBoxLayout, QDialog  # Import necessary widgets from PyQt5
from PyQt5.QtCore import QThread, pyqtSignal, QObject, QTimer  # Import necessary QtCore classes
from collections import deque  # Import deque for efficient appending and popping from both ends of a list
import numpy as np  # Import numpy for numerical operations
from graphs.graph_acceleration import graph_acceleration  # Import the graph_acceleration class
from graphs.graph_altitude import graph_altitude  # Import the graph_altitude class
from graphs.graph_gyro import graph_gyro  # Import the graph_gyro class
from graphs.graph_pressure import graph_pressure  # Import the graph_pressure class
from graphs.graph_temperature import graph_temperature  # Import the graph_temperature class
from graphs.graph_time import graph_time  # Import the graph_time class
from graphs.graph_humidity import graph_humidity  # Import the graph_humidity class
from dataBase import DataBase  # Import the DataBase class
from communication import Communication  # Import the Communication class
import serial  # Import the serial module for serial communication
import serial.tools.list_ports  # Import the serial.tools.list_ports module

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')  # Configure logging

class PortSelectionDialog(QDialog):
    """
    A dialog for selecting a serial port.

    Methods:
        __init__: Initializes the dialog.
        select_port: Selects a serial port.

    Attributes:
        selected_port: The selected serial port.
    """
    def __init__(self):
        """Initializes the PortSelectionDialog."""
        super().__init__()  # Call the constructor of the parent class (QDialog)
        self.setWindowTitle("Select Serial Port")  # Set the title of the dialog
        self.setFixedSize(600, 400)  # Set the fixed size of the dialog
        self.selected_port = None  # Initialize the selected_port to None

        main_layout = QVBoxLayout(self)  # Create a vertical layout for the dialog
        main_layout.setContentsMargins(20, 20, 20, 20)  # Set the margins of the layout

        title_label = QLabel("Available Serial Ports:")  # Create a label for the title
        title_label.setAlignment(QtCore.Qt.AlignTop)  # Align the title label to the top
        title_label.setStyleSheet("""QLabel { color: rgb(197, 198, 199); font-size: 20px; margin-bottom: 20px; }""")  # Set the stylesheet for the title label
        main_layout.addWidget(title_label)  # Add the title label to the main layout

        ports_layout = QVBoxLayout()  # Create a vertical layout for the ports
        main_layout.addLayout(ports_layout)  # Add the ports layout to the main layout

        main_layout.addStretch(1)  # Add a stretch to the main layout

        available_ports = [port.device for port in serial.tools.list_ports.comports()]  # Get a list of available serial ports

        if not available_ports:  # If no serial ports are found
            label = QLabel("No serial ports found.")  # Create a label indicating no ports were found
            label.setAlignment(QtCore.Qt.AlignTop)  # Align the label to the top
            label.setStyleSheet("""QLabel { color: rgb(197, 198, 199); font-size: 16px; margin-bottom: 10px; }""")  # Set the stylesheet for the label
            ports_layout.addWidget(label)  # Add the label to the ports layout
        else:  # If serial ports are found
            for port in available_ports:  # Iterate through the available ports
                button = QPushButton(port)  # Create a button for each port
                button.setStyleSheet("""QPushButton { background-color:rgb(29, 185, 84); color:rgb(0,0,0); font-size:16px; padding: 12px; border-radius: 5px; margin-bottom: 10px; } QPushButton:hover { background-color: rgb(29, 130, 84); }""")  # Set the stylesheet for the button
                button.clicked.connect(lambda checked, p=port: self.select_port(p))  # Connect the button's clicked signal to the select_port method
                ports_layout.addWidget(button)  # Add the button to the ports layout

        self.setStyleSheet("""QDialog { background-color: rgb(33, 33, 33); }""")  # Set the stylesheet for the dialog

    def select_port(self, port):
        """Selects a serial port."""
        self.selected_port = port  # Set the selected_port to the given port
        self.accept()  # Accept the dialog

class DataWorker(QObject):
    """
    Worker class for emitting signals from the data acquisition thread.

    Signals:
        data_received: Emitted when data is received.
    """
    data_received = pyqtSignal(list)  # Define a pyqtSignal to emit received data

class DataAcquisitionThread(QThread):
    """
    Thread to handle data acquisition from the serial port.

    Methods:
        __init__: Initializes the thread.
        run: Runs the data acquisition loop.
        stop: Stops the thread.

    Attributes:
        communication: The communication object for serial communication.
        running: A flag indicating whether the thread is running.
        data_worker: The data worker object for emitting signals.
    """
    def __init__(self, communication: Communication, data_worker: DataWorker):
        """Initializes the DataAcquisitionThread."""
        super().__init__()  # Call the constructor of the parent class (QThread)
        self.communication = communication  # Store the communication object
        self.running = True  # Set the running flag to True
        self.data_worker = data_worker  # Store the data worker object

    def run(self):
        """Runs the data acquisition thread."""
        while self.running:  # While the thread is running
            try:
                str_value_chain = self.communication.getData()  # Get data from the serial port as a string
                # Use numpy for faster conversion
                try:
                    value_chain = np.array(str_value_chain, dtype=float)  # Convert the string data to a numpy array of floats
                except ValueError as e:  # Handle ValueError during conversion
                    print(f"ValueError during conversion: {e}, Data: {str_value_chain}")  # Print the error message and the data
                    continue  # Skip this iteration if conversion fails

                if value_chain.size == 11:  # Check if the value chain has 11 elements
                    self.data_worker.data_received.emit(value_chain.tolist())  # Emit the data_received signal with the value chain as a list

            except Exception as e:  # Handle other exceptions
                print(f"Error in DataAcquisitionThread: {e}")  # Print the error message

            self.msleep(5)  # Reduced sleep time (adjustable) - Sleep for 5 milliseconds

    def stop(self):
        """Stops the data acquisition thread."""
        self.running = False  # Set the running flag to False

class PlottingThread(QThread):
    """
    Thread to handle graph updates.

    Methods:
        __init__: Initializes the thread.
        run: Runs the plotting loop.
        stop: Stops the thread.

    Attributes:
        gui: The GUI object.
        data_base: The database object.
        running: A flag indicating whether the thread is running.
        time: The time graph object.
        altitude: The altitude graph object.
        acceleration: The acceleration graph object.
        gyro: The gyro graph object.
        pressure: The pressure graph object.
        temperature: The temperature graph object.
        ppm: The PPM graph object.
        humidity: The humidity graph object.
        altitude_data: A deque for storing altitude data.
        time_data: A deque for storing time data.
    """
    def __init__(self, gui, data_base):
        """Initializes the PlottingThread."""
        super().__init__()  # Call the constructor of the parent class (QThread)
        self.gui = gui  # Store the GUI object
        self.data_base = data_base  # Store the database object
        self.running = True  # Set the running flag to True

        # Initialize graph objects
        self.time = graph_time(font=self.gui.font)  # Initialize the time graph
        self.altitude = graph_altitude()  # Initialize the altitude graph
        self.acceleration = graph_acceleration()  # Initialize the acceleration graph
        self.gyro = graph_gyro()  # Initialize the gyro graph
        self.pressure = graph_pressure()  # Initialize the pressure graph
        self.temperature = graph_temperature()  # Initialize the temperature graph
        self.humidity = graph_humidity()  # Initialize the humidity graph

        # Initialize data storage for altitude and time
        self.altitude_data = deque(maxlen=100)  # Initialize a deque for altitude data with a maximum length of 100
        self.time_data = deque(maxlen=100)  # Initialize a deque for time data with a maximum length of 100

    def run(self):
        """Runs the plotting thread."""
        while self.running:  # While the thread is running
            self.msleep(50)  # Sleep for 50 milliseconds

    def stop(self):
        """Stops the plotting thread."""
        self.running = False  # Set the running flag to False

class FlightMonitoringGUI:
    """
    Main class for the flight monitoring GUI.

    Methods:
        __init__: Initializes the GUI, serial communication, and database.
        init_ui: Initializes the user interface.
        init_threads: Initializes and starts the data acquisition and plotting threads.
        update_graphs: Updates the graphs with new data.
        run: Runs the application event loop.
        cleanup: Stops the threads when the GUI is closed.

    Attributes:
        view: The main graphics view.
        Layout: The main graphics layout.
        ser: The serial communication object.
        data_base: The database object.
        font: The font used in the GUI.
        style: The style for the buttons.
        time: The time graph object.
        altitude: The altitude graph object.
        acceleration: The acceleration graph object.
        gyro: The gyro graph object.
        pressure: The pressure graph object.
        temperature: The temperature graph object.
        ppm: The PPM graph object.
        humidity: The humidity graph object.
        altitude_data: A deque for storing altitude data.
        time_data: A deque for storing time data.
        servo_thread: The servo control thread.
        data_worker: The data worker object.
        data_acquisition_thread: The data acquisition thread.
        plotting_thread: The plotting thread.
    """
    def __init__(self, selected_port=None):
        """Initializes the GUI, serial communication, and database."""
        # Graph settings
        pg.setConfigOption('background', (33, 33, 33))  # Set the background color of the graph
        pg.setConfigOption('foreground', (197, 198, 199))  # Set the foreground color of the graph

        self.view = pg.GraphicsView()  # Create a GraphicsView object
        self.Layout = pg.GraphicsLayout()  # Create a GraphicsLayout object
        self.view.setCentralItem(self.Layout)  # Set the central item of the GraphicsView to the GraphicsLayout
        self.view.show()  # Show the GraphicsView

        if sys.platform.startswith('win'):  # Check if the platform is Windows
            import os  # Import the os module
            directory = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the current file
            icon_path = os.path.join(directory, "icon.ico")  # Create the path to the icon file
            self.view.setWindowIcon(QtGui.QIcon(icon_path))  # Set the window icon
        self.view.setWindowTitle('Flight Monitoring with Servo Control')  # Set the window title
        self.view.resize(1200, 700)  # Set the size of the window

        # Initialize serial communication and database
        self.ser = Communication(port_name=selected_port)  # Initialize the serial communication object
        self.data_base = DataBase()  # Initialize the database object

        # Set font
        self.font = QtGui.QFont()  # Create a QFont object
        self.font.setPixelSize(90)  # Set the pixel size of the font

        # Define button style
        self.style = "background-color:rgb(29, 185, 84);color:rgb(0,0,0);font-size:14px;"  # Define the style for the buttons

        # Initialize graph objects
        self.time = graph_time(font=self.font)  # Initialize the time graph
        self.altitude = graph_altitude()  # Initialize the altitude graph
        self.acceleration = graph_acceleration()  # Initialize the acceleration graph
        self.gyro = graph_gyro()  # Initialize the gyro graph
        self.pressure = graph_pressure()  # Initialize the pressure graph
        self.temperature = graph_temperature()  # Initialize the temperature graph
        self.humidity = graph_humidity()  # Initialize the humidity graph

        # Initialize data storage for altitude and time
        self.altitude_data = deque(maxlen=100)  # Initialize a deque for altitude data with a maximum length of 100
        self.time_data = deque(maxlen=100)  # Initialize a deque for time data with a maximum length of 100

        # Create and start the servo control thread
        self.servo_thread = ServoControlThread(self.ser)  # Pass communication object
        self.servo_thread.start()  # Start the servo control thread

        # Initialize the user interface
        self.init_ui()  # Initialize the user interface

        # Set up threads and start data acquisition
        self.init_threads()  # Initialize the threads

    def init_ui(self):
        """Initializes the user interface."""
        # Add title at the top
        self.Layout.addLabel("ITS NOT ROCKET SCIENCE", col=1, colspan=11)  # Add a label to the layout
        self.Layout.nextRow()  # Move to the next row in the layout

        # Add Start/Stop Storage buttons
        proxy1 = QtWidgets.QGraphicsProxyWidget()  # Create a proxy widget
        self.save_button = QPushButton('Start Storage')  # Create a button to start storage
        self.save_button.setStyleSheet(self.style)  # Set the style of the button
        self.save_button.clicked.connect(self.data_base.start_storage)  # Connect the button's clicked signal to the start_storage method of the database object
        proxy1.setWidget(self.save_button)  # Set the widget of the proxy widget

        proxy2 = QtWidgets.QGraphicsProxyWidget()  # Create a proxy widget
        self.end_save_button = QPushButton('Stop Storage')  # Create a button to stop storage
        self.end_save_button.setStyleSheet(self.style)  # Set the style of the button
        self.end_save_button.clicked.connect(self.data_base.stop_storage)  # Connect the button's clicked signal to the stop_storage method of the database object
        proxy2.setWidget(self.end_save_button)  # Set the widget of the proxy widget

        proxy3 = QtWidgets.QGraphicsProxyWidget()  # Create a proxy widget
        self.start_stop_button = QPushButton('Start/Stop Cansat')  # Create a button to start/stop the Cansat
        self.start_stop_button.setStyleSheet(self.style)  # Set the style of the button
        self.start_stop_button.clicked.connect(lambda: self.ser.serial_send("start_stop"))  # Connect the button's clicked signal to the serial_send method of the serial object
        proxy3.setWidget(self.start_stop_button)  # Set the widget of the proxy widget

        lb = self.Layout.addLayout(colspan=21)  # Create a layout
        lb.addItem(proxy1)  # Add the proxy widget to the layout
        lb.nextCol()  # Move to the next column
        lb.addItem(proxy2)  # Add the proxy widget to the layout
        lb.nextCol()  # Move to the next column
        lb.addItem(proxy3)  # Add the proxy widget to the layout

        self.Layout.nextRow()  # Move to the next row

        # Create layout for graphs
        l1 = self.Layout.addLayout(colspan=20, rowspan=4)  # Create a layout for the graphs

        # Row 1: Altitude, Time
        l11 = l1.addLayout(rowspan=1, border=(83, 83, 83))  # Create a layout for the first row
        l11.addItem(self.altitude)  # Add the altitude graph to the layout
        l11.addItem(self.pressure)  # Add the pressure graph to the layout
        l11.addItem(self.time)  # Add the time graph to the layout

        self.time.setFixedHeight(200)  # Set the fixed height of the time graph
        self.time.setFixedWidth(300)  # Set the fixed width of the time graph

        l1.nextRow()  # Move to the next row

        # Row 2: Acceleration, Gyro, Pressure, Temperature
        l12 = l1.addLayout(rowspan=1, border=(83, 83, 83))  # Create a layout for the second row
        l12.addItem(self.acceleration)  # Add the acceleration graph to the layout
        self.acceleration.setFixedHeight(170)  # Set the fixed height of the acceleration graph
        self.acceleration.setFixedWidth(400)  # Set the fixed width of the acceleration graph

        l12.addItem(self.gyro)  # Add the gyro graph to the layout
        self.gyro.setFixedHeight(170)  # Set the fixed height of the gyro graph
        self.gyro.setFixedWidth(400)  # Set the fixed width of the gyro graph

        l12.addItem(self.temperature)  # Add the temperature graph to the layout
        self.temperature.setFixedHeight(170)  # Set the fixed height of the gyro graph
        l1.nextRow()  # Move to the next row

        # Row 3: Humidity, PPM
        l13 = l1.addLayout(rowspan=1, border=(83, 83, 83))  # Create a layout for the third row
        l13.addItem(self.humidity)  # Add the humidity graph to the layout
        self.humidity.setFixedHeight(170)  # Set the fixed height of the acceleration graph
        self.Layout.nextRow()  # Create ServoControl widget and add it to layout

        self.servo_control_widget = ServoControl(self.servo_thread)  # Remove communication object
        proxy3 = QtWidgets.QGraphicsProxyWidget()  # Create a proxy widget
        proxy3.setWidget(self.servo_control_widget)  # Set the widget of the proxy widget

        l1.nextRow()  # Move to the next row
        l14 = l1.addLayout(rowspan=1, colspan=20, border=(83, 83, 83))  # Create a layout for the fourth row
        l14.addItem(proxy3)  # Add the proxy widget to the layout

    def init_threads(self):
        """Initialize and start the data acquisition and plotting threads."""
        self.data_worker = DataWorker()  # Create a DataWorker object
        self.data_acquisition_thread = DataAcquisitionThread(self.ser, self.data_worker)  # Create a DataAcquisitionThread object
        self.plotting_thread = PlottingThread(self, self.data_base)  # Create a PlottingThread object

        self.data_worker.data_received.connect(self.update_graphs)  # Connect the data_received signal of the DataWorker object to the update_graphs method
        self.data_acquisition_thread.start()  # Start the data acquisition thread
        self.plotting_thread.start()  # Start the plotting thread

    def update_graphs(self, value_chain):
        """Update the graphs with new data. This runs in the *main* thread."""

        try:
            # Extract data
            altitude = value_chain[4]  # Extract the altitude from the value chain
            time = value_chain[0]  # Extract the time from the value chain
            acceleration = value_chain[8:11]  # Extract the acceleration from the value chain
            gyro = value_chain[5:8]  # Extract the gyro from the value chain
            pressure = value_chain[3]  # Extract the pressure from the value chain
            temperature = value_chain[2]  # Extract the temperature from the value chain
            humidity = value_chain[1]  # Extract the humidity from the value chain

            # Update graphs
            self.altitude.update(altitude)  # Update the altitude graph
            self.time.update(time)  # Update the time graph
            self.acceleration.update(*acceleration)  # Update the acceleration graph
            self.gyro.update(*gyro)  # Update the gyro graph
            self.pressure.update(pressure)  # Update the pressure graph
            self.temperature.update(temperature)  # Update the temperature graph
            self.humidity.update(humidity)  # Update the humidity graph

            # Save data to the database
            self.data_base.store_data(value_chain)  # Store the data in the database

        except Exception as e:  # Handle IndexError and ValueError exceptions
            logging.warning(f"Error updating graphs: {e}")  # Print the error message

    def run(self):
        """Runs the application event loop."""
        try:
            if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):  # Check if the application is running in interactive mode or if PyQt is not available
                sys.exit(self.app.exec_())  # Exit the application
        finally:
            self.cleanup()  # Call the cleanup method

    def cleanup(self):
        """Stop the threads when the GUI is closed."""
        self.data_acquisition_thread.stop()  # Stop the data acquisition thread
        self.plotting_thread.stop()  # Stop the plotting thread
        self.servo_thread.stop()  # Stop the servo thread
        self.data_acquisition_thread.wait()  # Wait for the data acquisition thread to finish
        self.plotting_thread.wait()  # Wait for the plotting thread to finish
        self.servo_thread.wait()  # Wait for the servo thread to finish

# Servo Control Thread for Independent Execution
class ServoControlThread(QThread):
    """
    Thread to handle servo control.

    Methods:
        __init__: Initializes the thread.
        run: Runs the servo control loop.
        add_command: Adds a command to the servo queue.
        stop: Stops the thread.

    Attributes:
        servo_signal: Signal to send servo data (servo ID and angle).
        running: A flag indicating whether the thread is running.
        queue: Queue to store servo commands.
        serial_communication: The communication object for serial communication.
    """
    servo_signal = pyqtSignal(int, int)  # Signal to send servo data (servo ID and angle)
    def __init__(self, serial_communication: Communication):  # Add serial communication object
        """Initializes the ServoControlThread."""
        super().__init__()  # Call the constructor of the parent class (QThread)
        self.running = True  # Set the running flag to True
        self.queue = []  # Queue to store servo commands
        self.serial_communication = serial_communication  # Store communication object

    def run(self):
        """Runs the servo control thread."""
        while self.running:  # While the thread is running
            if self.queue:  # Check if there are any commands in the queue
                servo1, servo2 = self.queue.pop(0)  # Get the first command from the queue
                # Implement Servo Control Logic Here
                data = f"{servo1},{servo2}"  # Create the data string
                self.serial_communication.serial_send(data)  # Use communication object to send data
                self.msleep(50)  # Rate Limiting - Sleep for 50 milliseconds
            else:
                self.msleep(10)  # Sleep for 10 milliseconds

    def add_command(self, angle1, angle2):
        """Adds a command to the servo queue."""
        self.queue.append((angle1, angle2))  # Add the command to the queue

    def stop(self):
        """Stops the servo control thread."""
        self.running = False  # Set the running flag to False

class ServoControl(QWidget):
    """
    Widget for controlling the servos.

    Methods:
        __init__: Initializes the widget.
        initUI: Initializes the user interface.
        slider1_moved: Called when slider 1 is moved.
        slider2_moved: Called when slider 2 is moved.
        send_servo1_command: Sends the servo 1 command if the slider hasn't moved for a while.
        send_servo2_command: Sends the servo 2 command if the slider hasn't moved for a while.
        update_servo_angle: Update servo angle using the ServoControlThread.

    Attributes:
        servo_thread: The servo control thread object.
        servo1_timer: Timer for servo 1.
        servo2_timer: Timer for servo 2.
        servo1_current_value: Current value of servo 1.
        servo2_current_value: Current value of servo 2.
        servo1_is_moving: Flag to indicate if servo 1 is moving.
        servo2_is_moving: Flag to indicate if servo 2 is moving.
    """
    def __init__(self, servo_thread: ServoControlThread):  # Remove communication object
        """Initializes the ServoControl widget."""
        super().__init__()  # Call the constructor of the parent class (QWidget)
        self.servo_thread = servo_thread  # Store the servo thread object
        self.initUI()  # Initialize the user interface
        self.servo1_timer = QTimer()  # Create a timer for servo 1
        self.servo1_timer.timeout.connect(self.send_servo1_command)  # Connect the timer's timeout signal to the send_servo1_command method

        self.servo2_timer = QTimer()  # Create a timer for servo 2
        self.servo2_timer.timeout.connect(self.send_servo2_command)  # Connect the timer's timeout signal to the send_servo2_command method

        self.servo1_current_value = 0  # Default angle
        self.servo2_current_value = 0  # Default angle
        self.servo1_is_moving = False  # Flag to indicate if servo 1 is moving
        self.servo2_is_moving = False  # Flag to indicate if servo 2 is moving

    def initUI(self):
        """Initializes the user interface for the servo control widget."""
        main_layout = QVBoxLayout()  # Create a vertical layout
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
""")  # Set the stylesheet for the widget

        # Servo 1 Control
        servo1_layout = QHBoxLayout()  # Create a horizontal layout for servo 1
        servo1_label = QLabel("Servo 1 Angle:")  # Create a label for servo 1
        self.servo1_slider = QSlider(QtCore.Qt.Horizontal)  # Create a slider for servo 1
        self.servo1_slider.setRange(0, 180)  # Set the range of the slider
        self.servo1_slider.setValue(0)  # Default angle
        self.servo1_value_label = QLabel(str(self.servo1_slider.value()))  # Create a label to display the value of the slider
        self.servo1_slider.valueChanged.connect(lambda value: self.slider1_moved(value))  # Connect the slider's valueChanged signal to the slider1_moved method
        self.servo1_value_label.valueChanged = lambda value: self.servo1_value_label.setText(str(value))  # if the value is changed on the label change the label text
        servo1_layout.addWidget(servo1_label)  # Add the label to the layout
        servo1_layout.addWidget(self.servo1_slider)  # Add the slider to the layout
        servo1_layout.addWidget(self.servo1_value_label)  # Add the value label to the layout
        main_layout.addLayout(servo1_layout)  # Add the layout to the main layout

        # Servo 2 Control (Example)
        servo2_layout = QHBoxLayout()  # Create a horizontal layout for servo 2
        servo2_label = QLabel("Servo 2 Angle:")  # Create a label for servo 2
        self.servo2_slider = QSlider(QtCore.Qt.Horizontal)  # Create a slider for servo 2
        self.servo2_slider.setRange(0, 180)  # Set the range of the slider
        self.servo2_slider.setValue(0)  # Default angle
        self.servo2_value_label = QLabel(str(self.servo2_slider.value()))  # Create a label to display the value of the slider
        self.servo2_slider.valueChanged.connect(lambda value: self.slider2_moved(value))  # Connect the slider's valueChanged signal to the slider2_moved method
        self.servo2_value_label.valueChanged = lambda value: self.servo2_value_label.setText(str(value))  # if the value is changed on the label change the label text
        servo2_layout.addWidget(servo2_label)  # Add the label to the layout
        servo2_layout.addWidget(self.servo2_slider)  # Add the slider to the layout
        servo2_layout.addWidget(self.servo2_value_label)  # Add the value label to the layout
        main_layout.addLayout(servo2_layout)  # Add the layout to the main layout

        self.setLayout(main_layout)  # Set the layout of the widget

    def slider1_moved(self, value):
        """Called when the slider is moved."""
        self.servo1_current_value = value  # Set the current value of servo 1
        self.servo1_value_label.setText(str(value))  # Set the text of the value label
        self.servo1_timer.start(500)  # Adjust delay as needed - Start the timer
        self.servo1_is_moving = True  # Set the moving flag to True

    def slider2_moved(self, value):
        """Called when the slider is moved."""
        self.servo2_current_value = value  # Set the current value of servo 2
        self.servo2_value_label.setText(str(value))  # Set the text of the value label
        self.servo2_timer.start(500)  # Adjust delay as needed - Start the timer
        self.servo2_is_moving = True  # Set the moving flag to True

    def send_servo1_command(self):
        """Sends the servo command if the slider hasn't moved for a while."""
        if self.servo1_is_moving:  # Check if the slider is moving
            self.servo1_is_moving = False  # Set the moving flag to False
            self.update_servo_angle()  # Update the servo angle
            self.servo1_timer.stop()  # Stop the timer

    def send_servo2_command(self):
        """Sends the servo command if the slider hasn't moved for a while."""
        if self.servo2_is_moving:  # Check if the slider is moving
            self.servo2_is_moving = False  # Set the moving flag to False
            self.update_servo_angle()  # Update the servo angle
            self.servo2_timer.stop()  # Stop the timer

    def update_servo_angle(self):
        """Update servo angle using the ServoControlThread."""
        self.servo_thread.add_command(self.servo1_current_value, self.servo2_current_value)  # Add the command to the servo thread
        
def main():
    """Main function to run the flight monitoring application."""
    app = QtWidgets.QApplication(sys.argv)  # Create a QApplication object
    dialog = PortSelectionDialog()  # Create a PortSelectionDialog object
    
    if dialog.exec_() == QDialog.Accepted:  # Show the dialog and check if it was accepted
        selected_port = dialog.selected_port  # Get the selected port
    else:
        print("No port selected. Exiting.")  # Print a message if no port was selected
        return  # Return from the function
    
    gui = FlightMonitoringGUI(selected_port)  # Create a FlightMonitoringGUI object
    gui.app = app  # Set the app attribute of the GUI object
    gui.run()  # Run the GUI

if __name__ == '__main__':
    main()  # Call the main function if the script is run directly