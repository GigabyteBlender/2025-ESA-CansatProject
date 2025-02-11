import time
from micropython import const
from adafruit_bus_device import i2c_device
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from adafruit_register.i2c_bits import RWBits
from busio import I2C

_I2C_ADDR = const(0x69)
_REG_WHOAMI = const(0x00)
_ERROR_CODE = const(0x02)
_COMMAND = const(0x7E)
_ACCEL_CONFIG = const(0x40)
_ACC_RANGE = const(0x41)
_GYRO_CONFIG = const(0x42)
_GYRO_RANGE = const(0x43)

# RESET Command
RESET_COMMAND = const(0xB6)

# Acceleration Output Rate HZ
BANDWIDTH_25_32 = const(0b0001)  # 25/32 Hz
BANDWIDTH_25_16 = const(0b0010)  # 25/16 Hz
BANDWIDTH_25_8 = const(0b0011)  # 25/8 Hz
BANDWIDTH_25_4 = const(0b0100)  # 25/4 Hz
BANDWIDTH_25_2 = const(0b0101)  # 25/2 Hz
BANDWIDTH_25 = const(0b0110)  # 25 Hz
BANDWIDTH_50 = const(0b0111)  # 50 Hz
BANDWIDTH_100 = const(0b1000)  # 100 Hz
BANDWIDTH_200 = const(0b1001)  # 200 Hz
BANDWIDTH_400 = const(0b1010)  # 400 Hz
BANDWIDTH_800 = const(0b1011)  # 800 Hz
BANDWIDTH_1600 = const(0b1100)  # 1600 Hz
BANDWIDTH_3200 = const(0b1101)  # 3200 Hz
bandwidth_values = (
    BANDWIDTH_25_32,
    BANDWIDTH_25_16,
    BANDWIDTH_25_8,
    BANDWIDTH_25_4,
    BANDWIDTH_25_2,
    BANDWIDTH_25,
    BANDWIDTH_50,
    BANDWIDTH_100,
    BANDWIDTH_200,
    BANDWIDTH_400,
    BANDWIDTH_800,
    BANDWIDTH_1600,
    BANDWIDTH_3200,
)
gyro_bandwidth_values = (
    BANDWIDTH_25,
    BANDWIDTH_50,
    BANDWIDTH_100,
    BANDWIDTH_200,
    BANDWIDTH_400,
    BANDWIDTH_800,
    BANDWIDTH_1600,
    BANDWIDTH_3200,
)

# Acceleration Range
ACCEL_RANGE_2G = const(0b0011)
ACCEL_RANGE_4G = const(0b0101)
ACCEL_RANGE_8G = const(0b1000)
ACCEL_RANGE_16G = const(0b1100)
acc_range_values = (ACCEL_RANGE_2G, ACCEL_RANGE_4G, ACCEL_RANGE_8G, ACCEL_RANGE_16G)

# UNDERSAMPLE
NO_UNDERSAMPLE = const(0)
UNDERSAMPLE = const(1)
acc_sample_values = (NO_UNDERSAMPLE, UNDERSAMPLE)

# Bandwidth Parameter
FILTER = const(0)
AVERAGING = const(1)
acc_bandwidth_values = (FILTER, AVERAGING)

# Acceleration Data
ACC_X_LSB = const(0x12)
ACC_Y_LSB = const(0x14)
ACC_Z_LSB = const(0x16)

# Acc Power Modes
ACC_POWER_SUSPEND = const(0x10)
ACC_POWER_NORMAL = const(0x11)
ACC_POWER_LOWPOWER = const(0x12)
acc_power_mode_values = (ACC_POWER_LOWPOWER, ACC_POWER_NORMAL, ACC_POWER_SUSPEND)

# Temperature
TEMP_LSB = const(0x20)

# Gyro Data
GYRO_X_LSB = const(0x0C)
GYRO_Y_LSB = const(0x0E)
GYRO_Z_LSB = const(0x10)

# Gyro Cutoffs
GYRO_NORMAL = const(0b10)
GYRO_OSR2 = const(0b01)
GYRO_OSR4 = const(0b00)
gyro_cutoffs_values = (GYRO_OSR4, GYRO_OSR2, GYRO_NORMAL)

# Gyro Power Modes
GYRO_POWER_SUSPEND = const(0x14)
GYRO_POWER_NORMAL = const(0x15)
GYRO_POWER_FASTSTARTUP = const(0x17)
gyro_power_modes = (GYRO_POWER_SUSPEND, GYRO_POWER_NORMAL, GYRO_POWER_FASTSTARTUP)

# Gyro Ranges
GYRO_RANGE_2000 = const(0b000)
GYRO_RANGE_1000 = const(0b001)
GYRO_RANGE_500 = const(0b010)
GYRO_RANGE_250 = const(0b011)
GYRO_RANGE_125 = const(0b100)
gyro_values = (
    GYRO_RANGE_125,
    GYRO_RANGE_250,
    GYRO_RANGE_500,
    GYRO_RANGE_1000,
    GYRO_RANGE_2000,
)

STANDARD_GRAVITY = 9.80665


class BMI160:

    _device_id = ROUnaryStruct(_REG_WHOAMI, "B")
    _soft_reset = UnaryStruct(_COMMAND, "B")
    _error_code = UnaryStruct(_ERROR_CODE, "B")
    _acc_config = UnaryStruct(_ACCEL_CONFIG, "B")
    _power_mode = UnaryStruct(0x03, "B")
    _gyro_config = UnaryStruct(_GYRO_CONFIG, "B")

    # Acceleration Data
    _acc_data_x = UnaryStruct(ACC_X_LSB, "<h")
    _acc_data_y = UnaryStruct(ACC_Y_LSB, "<h")
    _acc_data_z = UnaryStruct(ACC_Z_LSB, "<h")
    _read = UnaryStruct(_COMMAND, "B")

    # ACC_CONF Register (0x40)
    # Sets the output data rate, the bandwidth, and the read mode of the acceleration
    # sensor
    _acc_us = RWBits(1, _ACCEL_CONFIG, 7)
    _acc_bwp = RWBits(1, _ACCEL_CONFIG, 6)
    _acc_odr = RWBits(4, _ACCEL_CONFIG, 0)

    # ACC_RANGE Register (0x41)
    # The register allows the selection of the accelerometer g-range
    _acc_range = RWBits(4, _ACC_RANGE, 0)
    acceleration_scale = {
        "ACCEL_RANGE_2G": 16384,
        "ACCEL_RANGE_4G": 8192,
        "ACCEL_RANGE_8G": 4096,
        "ACCEL_RANGE_16G": 2048,
    }
    gyro_scale = {
        "GYRO_RANGE_125": 16.4,
        "GYRO_RANGE_250": 32.8,
        "GYRO_RANGE_500": 65.6,
        "GYRO_RANGE_1000": 131.2,
        "GYRO_RANGE_2000": 262.4,
    }

    # Temperature
    _temp_data = UnaryStruct(TEMP_LSB, "<h")

    # Gyro Data
    _gyro_data_x = UnaryStruct(GYRO_X_LSB, "<h")
    _gyro_data_y = UnaryStruct(GYRO_Y_LSB, "<h")
    _gyro_data_z = UnaryStruct(GYRO_Z_LSB, "<h")

    # GYRO_CONF Register (0x41)
    # Sets the output data rate, the bandwidth, and the read mode of the gyro
    # sensor
    _gyro_bwp = RWBits(2, _GYRO_CONFIG, 4)
    _gyro_odr = RWBits(4, _GYRO_CONFIG, 0)

    # GYRO_RANGE Register (0x43)
    _gyro_range = RWBits(3, _GYRO_RANGE, 0)

    def __init__(self, i2c_bus: I2C, address: int = _I2C_ADDR) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)

        if self._device_id != 0xD1:
            raise RuntimeError("Failed to find BMI160")

        self.soft_reset()

        self._read = 0x03
        time.sleep(0.1)
        self._read = ACC_POWER_NORMAL
        time.sleep(0.1)
        self._read = GYRO_POWER_NORMAL
        time.sleep(0.1)

    def soft_reset(self) -> None:
        """
        Performs a Soft Reset

        :return: None

        """
        self._soft_reset = RESET_COMMAND
        time.sleep(0.015)

    def error_code(self) -> None:

        code_errors = {
            0: "No Error",
            1: "Error",
            2: "Error",
            3: "low-power mode and interrupt uses pre-filtered data",
            6: "ODRs of enabled sensors in header-less mode do not match",
            7: "pre-filtered data are used in low power mode",
        }
        errors = self._error_code
        drop_cmd_err = (errors & 0x40) >> 6
        error_codes = (errors & 0x1E) >> 1
        fatal_error = errors & 0x01
        if drop_cmd_err:
            print("Drop Command Error")
        if code_errors[error_codes] != "No Error":
            print(code_errors[error_codes])
        if fatal_error:
            print("Fatal Error")

    @property
    def acceleration_undersample(self) -> str:

        sample_values = ("NO_UNDERSAMPLE", "UNDERSAMPLE")
        return sample_values[self._acc_us]

    @acceleration_undersample.setter
    def acceleration_undersample(self, value: int) -> None:
        if value not in acc_sample_values:
            raise ValueError("Value must be a valid acceleration undersample value")
        self._acc_us = value

    @property
    def acceleration_bandwidth_parameter(self) -> str:

        values = ("FILTER", "AVERAGING")
        return values[self._acc_bwp]

    @acceleration_bandwidth_parameter.setter
    def acceleration_bandwidth_parameter(self, value: int) -> None:
        if value not in acc_bandwidth_values:
            raise ValueError("Value must a be a valid Acceleration bandwidth setting")
        self._acc_bwp = value

    @property
    def acceleration_output_data_rate(self) -> str:

        values = (
            "BANDWIDTH_25_32",
            "BANDWIDTH_25_16",
            "BANDWIDTH_25_8",
            "BANDWIDTH_25_4",
            "BANDWIDTH_25_2",
            "BANDWIDTH_25",
            "BANDWIDTH_50",
            "BANDWIDTH_100",
            "BANDWIDTH_200",
            "BANDWIDTH_400",
            "BANDWIDTH_800",
            "BANDWIDTH_1600",
            "BANDWIDTH_3200",
        )
        return values[self._acc_odr]

    @acceleration_output_data_rate.setter
    def acceleration_output_data_rate(self, value: int) -> None:
        if value not in bandwidth_values:
            raise ValueError("Value must be a valid Acceleration Data Rate setting")
        self._acc_odr = value

    @property
    def acceleration_range(self) -> str:

        values = {
            3: "ACCEL_RANGE_2G",
            5: "ACCEL_RANGE_4G",
            8: "ACCEL_RANGE_8G",
            12: "ACCEL_RANGE_16G",
        }
        return values[self._acc_range]

    @acceleration_range.setter
    def acceleration_range(self, value: int) -> None:
        if value not in acc_range_values:
            raise ValueError("Value must be a valid Acceleration Range setting")
        self._acc_range = value

    @property
    def acceleration(self) -> str:
        """
        Acceleration Values
        """
        factor = self.acceleration_scale[self.acceleration_range]

        x = self._acc_data_x / factor * STANDARD_GRAVITY
        y = self._acc_data_y / factor * STANDARD_GRAVITY
        z = self._acc_data_z / factor * STANDARD_GRAVITY
        return x, y, z

    def power_mode_status(self) -> None:
        """
        Power mode status
        """
        values = self._power_mode

        acc_pmu_status = (values & 0x18) >> 4
        gyr_pmu_status = (values & 0xC) >> 2
        mag_pmu_status = values & 0x03

        acc_pmu_codes = {0: "Suspend", 1: "Normal", 2: "Low Power"}
        gyr_pmu_codes = {0: "Suspend", 1: "Normal", 3: "Fast Start - Up"}
        mag_pmu_codes = {0: "Suspend", 1: "Normal", 2: "Low Power"}

        print("Acceleration Power Mode: ", acc_pmu_codes[acc_pmu_status])
        print("Gyro Power Mode", gyr_pmu_codes[gyr_pmu_status])
        print("Mag Power Mode", mag_pmu_codes[mag_pmu_status])

    def acc_power_mode(self, value: int) -> None:

        if value not in acc_power_mode_values:
            raise ValueError("Value must be a valid Acceleration Power Mode Setting")
        self._read = value
        time.sleep(0.1)

    @property
    def temperature(self) -> int:

        return (self._temp_data * 1 / 2**9) + 23

    @property
    def gyro(self) -> str:
        """
        Gyro Values

        """
        factor = self.gyro_scale[self.gyro_range]

        x = self._gyro_data_x / factor
        y = self._gyro_data_y / factor
        z = self._gyro_data_z / factor
        return x, y, z

    @property
    def gyro_output_data_rate(self) -> str:

        values = (
            "BANDWIDTH_25",
            "BANDWIDTH_50",
            "BANDWIDTH_100",
            "BANDWIDTH_200",
            "BANDWIDTH_400",
            "BANDWIDTH_800",
            "BANDWIDTH_1600",
            "BANDWIDTH_3200",
        )

        return values[self._gyro_odr]

    @gyro_output_data_rate.setter
    def gyro_output_data_rate(self, value: int) -> None:
        if value not in gyro_bandwidth_values:
            raise ValueError("Value must be a valid Gyro Data Rate setting")
        self._gyro_odr = value

    @property
    def gyro_bandwidth_parameter(self) -> str:

        values = ("GYRO_OSR4", "GYRO_OSR2", "GYRO_NORMAL")
        return values[self._gyro_bwp]

    @gyro_bandwidth_parameter.setter
    def gyro_bandwidth_parameter(self, value: int) -> None:
        if value not in gyro_cutoffs_values:
            raise ValueError("Value must be a valid Gyro Bandwidth setting")
        self._gyro_bwp = value

    @property
    def gyro_power_mode(self) -> str:

        g_power_modes = {
            0x14: "GYRO_POWER_SUSPEND",
            0x15: "GYRO_POWER_NORMAL",
            0x17: "GYRO_POWER_FASTSTARTUP",
        }

        return g_power_modes[self._read]

    @gyro_power_mode.setter
    def gyro_power_mode(self, value: int) -> None:
        if value not in gyro_power_modes:
            raise ValueError("Value must be a valid Gyro Power Mode")

        self._read = value
        time.sleep(0.1)

    @property
    def gyro_range(self) -> str:

        g_values = (
            "GYRO_RANGE_125",
            "GYRO_RANGE_250",
            "GYRO_RANGE_500",
            "GYRO_RANGE_1000",
            "GYRO_RANGE_2000",
        )

        return g_values[self._gyro_range]

    @gyro_range.setter
    def gyro_range(self, value: int) -> None:
        if value not in gyro_values:
            raise ValueError("Value must be a valid Gyro range")
        self._gyro_range = value
