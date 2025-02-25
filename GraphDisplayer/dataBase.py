import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataBase:  # Class names should be capitalized
    """
    A class for handling data storage to a file.

    Attributes:
        file_path (str): The path to the data file.
        state (bool): A flag indicating whether data storage is active (default: False).

    Methods:
        __init__(): Initializes the DataBase object and creates the data file if it doesn't exist.
        create_file(): Creates the data file with a header row.
        store_data(data): Appends the given data to the data file, if storage is active.
        start_storage(): Starts data storage.
        stop_storage(): Stops data storage.
    """

    def __init__(self, filename="flight_data.txt"):  # Added filename parameter
        """
        Initializes the DataBase object.

        Sets the initial state to False, constructs the file path, and creates the file if it doesn't exist.
        """
        self.state = False
        self.filename = filename
        self.file_path = self.get_file_path()
        self.create_file()

    def get_file_path(self):
        """
        Constructs the file path.

        Returns:
            str: The absolute path to the data file.
        """
        directory = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(directory, self.filename)

    def create_file(self):
        """
        Creates the data file with a header row if it doesn't exist.
        """
        if not os.path.exists(self.file_path):  # Check if file exists
            try:
                with open(self.file_path, "w") as file:
                    file.write('Time,Humidity,Temperature,Pressure,Altitude,PPM,GyroX,GyroY,GyroZ,AccX,AccY,AccZ\n')
                logging.info(f"Created data file: {self.file_path}")
            except Exception as e:
                logging.error(f"Error creating data file: {e}")
        else:
            logging.info(f"Data file already exists: {self.file_path}")

    def store_data(self, data): #Renamed from guardar to store_data for clarity
        """
        Appends the given data to the data file, along with a timestamp, if storage is active.

        Args:
            data (list): A list of data values to be stored.
        """
        if self.state:
            try:
                data_str = ', '.join(map(str, data))  # Convert data to comma-separated string
                log_string = f'{data_str}\n'
                with open(self.file_path, "a") as f:
                    f.write(log_string)
                logging.debug(f"Data stored: {log_string.strip()}") # Log data write
            except Exception as e:
                logging.error(f"Error writing to data file: {e}")

    def start_storage(self):#Renamed from start to start_storage for clarity
        """
        Starts data storage.
        """
        self.state = True
        logging.info('Data storage started.')

    def stop_storage(self):#Renamed from stop to stop_storage for clarity
        """
        Stops data storage.
        """
        self.state = False
        logging.info('Data storage stopped.')