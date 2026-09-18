"""
config.py

Central configuration for the AGCO Airflow Smoke Test Bench.

Raspberry Pi 4
GPIO numbering: BCM

Hardware:
    - 2 x Delta EFB0412VHD-SP05, 4-wire fans
    - 2 x OPT101 optical sensors
    - 2 x TLDR5800 red LEDs
    - ADS1115 ADC via I2C

The fans receive continuous 12 V.
Their dedicated PWM inputs are controlled through
inverting NPN transistor stages.

No hardware is initialized in this file.
"""

# ============================================================
# APPLICATION
# ============================================================

APP_NAME = "Airflow Smoke Test Bench"
APP_VERSION = "0.1.0"


# ============================================================
# HARDWARE MODE
# ============================================================

VALID_HARDWARE_MODES = ("simulation", "real")

# Keep simulation until physical hardware has been verified.
HARDWARE_MODE = "real"


# ============================================================
# FAN GPIO CONFIGURATION
# ============================================================

# BCM numbering.

# Fan 1: Main airflow fan
MAIN_FAN_PWM_GPIO = 18

# Fan 2: Smoke chamber fan
SMOKE_FAN_PWM_GPIO = 19

# Fan frequency-generator (FG) feedback.
# Reserved for future RPM measurement.
# Not implemented in the current software.
MAIN_FAN_FG_GPIO = 17
SMOKE_FAN_FG_GPIO = 27


# ============================================================
# LED CONFIGURATION
# ============================================================

"""
The LEDs are supplied directly from 12 V through
current-limiting resistors in the schematic.

They are NOT controlled by Raspberry Pi GPIO.

The following values are retained for compatibility
with existing code. They must not be used to
initialize physical LED GPIO outputs.
"""

SENSOR_1_LED_GPIO = 23
SENSOR_2_LED_GPIO = 24

LEDS_HARDWIRED = True


# ============================================================
# I2C CONFIGURATION
# ============================================================

I2C_BUS = 1

I2C_SDA_GPIO = 2
I2C_SCL_GPIO = 3

ADS1115_I2C_ADDRESS = 0x48


# ============================================================
# ADS1115 CHANNEL CONFIGURATION
# ============================================================

SENSOR_1_ADC_CHANNEL = 0
SENSOR_2_ADC_CHANNEL = 1

ADS1115_GAIN = 1


# ============================================================
# FAN PWM CONFIGURATION
# ============================================================

PWM_MIN_PERCENT = 0
PWM_MAX_PERCENT = 100

# Use a 1% step for fine-grained control.
# This keeps the full range 0..100 and allows values like
# 1, 2, 3, ... to be selected directly.
PWM_STEP_PERCENT = 1

PWM_LEVELS = tuple(
    range(
        PWM_MIN_PERCENT,
        PWM_MAX_PERCENT + PWM_STEP_PERCENT,
        PWM_STEP_PERCENT,
    )
)

DEFAULT_MAIN_FAN_PWM = 0
DEFAULT_SMOKE_FAN_PWM = 0

DEFAULT_MAIN_FAN_ACTIVE = False
DEFAULT_SMOKE_FAN_ACTIVE = False


# ============================================================
# PWM FREQUENCY AND POLARITY
# ============================================================

"""
Delta EFB0412VHD-SP05:

The fan is powered by continuous 12 V.

PWM is applied to its dedicated PWM input through
an inverting NPN transistor stage.

The transistor inverts the GPIO signal:

    GPIO HIGH -> fan PWM LOW
    GPIO LOW  -> fan PWM HIGH

The fan controller must compensate for this inversion.

100 Hz is used for the initial test.
The datasheet specifies 25 kHz as the preferred frequency,
which requires a suitable PWM backend.

IMPORTANT:
The fan can run at maximum speed if its PWM input is
disconnected or the Raspberry Pi stops driving the pin.

A physical 12 V power cut-off is required.
Software STOP ALL is not a hardware safety interlock.
"""

FAN_PWM_FREQUENCY_HZ = 100

FAN_PWM_INVERTED = True


# ============================================================
# SENSOR CONFIGURATION
# ============================================================

SENSOR_SAMPLE_RATE_HZ = 10

SENSOR_SAMPLE_INTERVAL_S = (
    1.0 / SENSOR_SAMPLE_RATE_HZ
)

DEFAULT_SENSOR_1_ACTIVE = False
DEFAULT_SENSOR_2_ACTIVE = False


# ============================================================
# SMOKE MACHINE
# ============================================================

"""
The smoke machine is controlled manually.

This state is only used for logging.
"""

DEFAULT_SMOKE_MACHINE_ACTIVE = False


# ============================================================
# SEQUENCE CONFIGURATION
# ============================================================

DEFAULT_SEQUENCE_RUNNING = False

MIN_SEQUENCE_STEP_DURATION_S = 0.1


# ============================================================
# LOGGING CONFIGURATION
# ============================================================

DATA_DIRECTORY = "data"

CSV_FILE_EXTENSION = ".csv"
VIDEO_FILE_EXTENSION = ".mp4"

CSV_DELIMITER = ";"

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


# ============================================================
# CAMERA CONFIGURATION
# ============================================================

DEFAULT_CAMERA_ENABLED = False
DEFAULT_CAMERA_RECORD_VIDEO = False

DEFAULT_CAMERA_RESOLUTION = (1920, 1080)
DEFAULT_CAMERA_PREVIEW_SIZE = (640, 360)
DEFAULT_CAMERA_TARGET_FPS = 30

CAMERA_NOT_AVAILABLE_TEXT = "NOT AVAILABLE"
CAMERA_OFF_TEXT = "OFF"
CAMERA_ON_TEXT = "CONNECTED"


# ============================================================
# CSV COLUMNS
# ============================================================
CSV_COLUMNS = (
    "timestamp",
    "elapsed_time_s",

    "main_fan_active",
    "main_fan_pwm_percent",
    "main_fan_rpm",

    "smoke_fan_active",
    "smoke_fan_pwm_percent",
    "smoke_fan_rpm",

    "smoke_machine_active",

    "sensor_1_active",
    "sensor_1_voltage_v",

    "sensor_2_active",
    "sensor_2_voltage_v",

    "sequence_running",
)
# ============================================================
# TEST METADATA
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
# STARTUP AND SAFETY
# ============================================================

"""
Controllable outputs must start OFF.

STOP ALL must:
    - Stop main fan
    - Stop smoke fan
    - Set both PWM values to 0 %
    - Stop any running sequence

STOP ALL must NOT:
    - Stop data recording

IMPORTANT:
Software cannot guarantee that the fans stop when
the Raspberry Pi is powered off, rebooting or crashed.

The fan power supply must have a physical cut-off.
"""

START_OUTPUTS_OFF = True