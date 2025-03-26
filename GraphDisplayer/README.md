# Flight Monitoring Application

## Overview

This is a sophisticated Flight Monitoring Application designed for tracking and visualizing data from a CanSat or similar small satellite/aerospace project. The application provides real-time graphical representation of various sensor data and includes servo control functionality.

## Features

- Real-time data visualization for multiple sensor parameters
- Graphs for:
  - Altitude
  - Acceleration (X, Y, Z axes)
  - Gyroscope (Pitch, Roll, Yaw)
  - Pressure
  - Temperature
  - Humidity
- Data storage capabilities
- Servo control interface
- Dynamic serial port selection

## Prerequisites

### Hardware
- A compatible device which sends the information over a serial port
- USB connection for serial communication
- Computer running Python

### Software Requirements
- Python 3.7+
- Required Python Libraries:
  - PyQt5
  - pyqtgraph
  - pyserial
  - numpy

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-repo/flight-monitoring-app.git
cd flight-monitoring-app
```

2. Install required dependencies:
```bash
pip install PyQt5 pyqtgraph pyserial numpy
```

## Application Components

### Main Components

1. `main.py`: 
   - Central application logic
   - Manages threads for data acquisition and plotting
   - Handles user interface initialization

2. `communication.py`:
   - Manages serial communication
   - Handles data transmission and reception
   - Supports dummy mode for testing

3. `dataBase.py`:
   - Manages data storage
   - Writes sensor data to text files
   - Provides start/stop storage functionality

### Graph Classes
Specialized classes for each sensor data type:
- `graph_acceleration.py`
- `graph_altitude.py`
- `graph_gyro.py`
- `graph_humidity.py`
- `graph_pressure.py`
- `graph_temperature.py`
- `graph_time.py`

## Usage

### Launching the Application

1. Connect your sensor module/CubeSat to the computer via USB
2. Run the application:
```bash
python main.py
```

3. In the port selection dialog, choose the appropriate serial port for your device

### User Interface

#### Main Window
- Title: "ITS NOT ROCKET SCIENCE"
- Graphs displaying real-time sensor data
- Buttons for controlling data storage and device state

#### Buttons
- `Start Storage`: Begin recording sensor data to file
- `Stop Storage`: Cease recording sensor data
- `Start/Stop Cansat`: Toggle the connected device's active state

#### Servo Control
- Two sliders for controlling servo angles (0-180 degrees)
- Adjustable servo positioning

### Data Storage

- Data is stored in a text file (default: `flight_data.txt`)
- Columns include: Time, Humidity, Temperature, Pressure, Altitude, PPM, GyroX, GyroY, GyroZ, AccX, AccY, AccZ

## Configuration

### Serial Communication
- Default Baud Rate: 9600
- Configurable in `communication.py`
- there is actually two serial ports being used. one for incoming and one for outcoming. Only the aoutcoming port can currently be easily selected with the GUI. the output port to send data to the device can be changed by simply changing the string to what it should be.

### Data Logging
- Modify `dataBase.py` to change file naming or storage location

## Troubleshooting

1. No serial ports detected:
   - Ensure device is connected
   - Check USB drivers
   - Verify device compatibility

2. No data displayed:
   - Confirm serial connection
   - Check sensor module configuration
   - Verify data transmission settings

## Contributing

Contributions are welcome! Please submit pull requests or open issues on the repository.

## Acknowledgments

- Developed as part of an aerospace/CanSat project
- Utilizes open-source libraries: PyQt, pyqtgraph, pyserial