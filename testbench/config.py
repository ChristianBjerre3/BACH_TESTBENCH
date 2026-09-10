"""
config.py

Central configuration for the airflow/smoke test bench.

This module contains ONLY constants and configuration values.
No GPIO, ADC, GUI, logging, or other hardware initialization
should be performed in this file.

GPIO numbering convention:
    BCM numbering

System:
    Raspberry Pi 4

Hardware overview:
    - Main 12 V fan controlled via MOSFET
    - Smoke 12 V fan controlled via MOSFET
    - 2 x OPT101 optical sensors
    - 2 x red LEDs
    - ADS1115 ADC connected through I2C
"""


# ============================================================
# GENERAL APPLICATION SETTINGS
# ============================================================

APP_NAME = "Airflow Smoke Test Bench"
APP_VERSION = "0.1.0"


# ============================================================
# HARDWARE MODE
# ============================================================

"""
Select which hardware backend the application uses.

Allowed values:
    "simulation" - in-memory backends under simulation/ (desktop testing)
    "real"       - physical Raspberry Pi hardware under hardware/

No automatic OS detection is performed. The mode must be set explicitly.
"""

VALID_HARDWARE_MODES = ("simulation", "real")

HARDWARE_MODE = "simulation"


# ============================================================
# GPIO CONFIGURATION
# ============================================================

# BCM GPIO numbering is used throughout the project.

# Main airflow fan
MAIN_FAN_PWM_GPIO = 18

# Smoke chamber fan
SMOKE_FAN_PWM_GPIO = 13

# LED associated with optical sensor 1
SENSOR_1_LED_GPIO = 23

# LED associated with optical sensor 2
SENSOR_2_LED_GPIO = 24


# ============================================================
# I2C CONFIGURATION
# ============================================================

# Standard Raspberry Pi 4 I2C bus
I2C_BUS = 1

# BCM pin numbers used by I2C
I2C_SDA_GPIO = 2
I2C_SCL_GPIO = 3

# Default ADS1115 I2C address when ADDR is connected to GND
ADS1115_I2C_ADDRESS = 0x48


# ============================================================
# ADS1115 CHANNEL CONFIGURATION
# ============================================================

# OPT101 sensor 1 is connected to ADS1115 channel A0
SENSOR_1_ADC_CHANNEL = 0

# OPT101 sensor 2 is connected to ADS1115 channel A1
SENSOR_2_ADC_CHANNEL = 1


# ============================================================
# FAN PWM CONFIGURATION
# ============================================================

PWM_MIN_PERCENT = 0
PWM_MAX_PERCENT = 100

# User-adjustable PWM levels in the GUI
PWM_STEP_PERCENT = 10

PWM_LEVELS = tuple(
    range(
        PWM_MIN_PERCENT,
        PWM_MAX_PERCENT + PWM_STEP_PERCENT,
        PWM_STEP_PERCENT,
    )
)

# Initial/default PWM when the application starts
DEFAULT_MAIN_FAN_PWM = 0
DEFAULT_SMOKE_FAN_PWM = 0

# Both fans should always start in OFF state
DEFAULT_MAIN_FAN_ACTIVE = False
DEFAULT_SMOKE_FAN_ACTIVE = False


# ============================================================
# PWM FREQUENCY
# ============================================================

"""
Initial PWM frequency for the two 2-wire BLDC fans.

Because these are 2-wire fans, PWM is applied to the fan supply
through the MOSFET rather than through a dedicated PWM control wire.

The final optimal frequency may depend on the specific fans.
This value can therefore be changed later without changing
the fan-control code.
"""

FAN_PWM_FREQUENCY_HZ = 100


# ============================================================
# SENSOR CONFIGURATION
# ============================================================

# Sampling rate for both OPT101 sensors
SENSOR_SAMPLE_RATE_HZ = 10

# Sampling interval calculated from the frequency
SENSOR_SAMPLE_INTERVAL_S = 1.0 / SENSOR_SAMPLE_RATE_HZ

# Sensors start disabled until enabled by the user
DEFAULT_SENSOR_1_ACTIVE = False
DEFAULT_SENSOR_2_ACTIVE = False


# ============================================================
# ADS1115 CONFIGURATION
# ============================================================

"""
ADS1115 gain.

Gain = 1 gives a full-scale input range of approximately:
    +/- 4.096 V

This is a sensible initial value.

The final gain may later be adjusted depending on the actual
OPT101 output-voltage range.
"""

ADS1115_GAIN = 1


# ============================================================
# SMOKE MACHINE LOGGING
# ============================================================

"""
The smoke machine is operated manually.

The Raspberry Pi does NOT control the smoke machine electrically.
This state only represents whether the operator has marked the
smoke machine as active in the GUI.
"""

DEFAULT_SMOKE_MACHINE_ACTIVE = False


# ============================================================
# SEQUENCE CONFIGURATION
# ============================================================

DEFAULT_SEQUENCE_RUNNING = False

# Minimum allowed sequence step duration
MIN_SEQUENCE_STEP_DURATION_S = 0.1


# ============================================================
# LOGGING CONFIGURATION
# ============================================================

DATA_DIRECTORY = "data"

CSV_FILE_EXTENSION = ".csv"

# Default delimiter chosen for easy processing in Python,
# MATLAB, R, Excel, etc.
CSV_DELIMITER = ";"

# Time format used for readable timestamps
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


# ============================================================
# CSV COLUMN DEFINITIONS
# ============================================================

CSV_COLUMNS = (
    "timestamp",
    "elapsed_time_s",

    "main_fan_active",
    "main_fan_pwm_percent",

    "smoke_fan_active",
    "smoke_fan_pwm_percent",

    "smoke_machine_active",

    "sensor_1_active",
    "sensor_1_voltage_v",

    "sensor_2_active",
    "sensor_2_voltage_v",

    "sequence_running",
)


# ============================================================
# TEST METADATA FIELDS
# ============================================================

TEST_METADATA_FIELDS = (
    "test_name",
    "mount_name",
    "comment",
    "date_time",
)


# ============================================================
# GUI DEFAULTS
# ============================================================

DEFAULT_TEST_NAME = ""
DEFAULT_MOUNT_NAME = ""
DEFAULT_TEST_COMMENT = ""

LIVE_PLOT_TIME_WINDOW_S = 30


# ============================================================
# SAFETY / STARTUP BEHAVIOUR
# ============================================================

"""
On application startup, all controllable outputs must be OFF.

The individual hardware modules will later use these values
during initialization.

STOP ALL will later:
    - Stop main fan
    - Stop smoke fan
    - Set both fan PWM values to 0 %
    - Stop any running sequence

STOP ALL will NOT:
    - Stop data recording
"""

START_OUTPUTS_OFF = True