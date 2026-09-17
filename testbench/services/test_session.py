"""
services/test_session.py

Central logical state for the AGCO Airflow Smoke Test Bench.

Stores:
    - Test metadata
    - Fan ON/OFF states
    - Requested fan PWM percentages
    - Measured fan RPM
    - Manually logged smoke-machine state
    - Optical sensor states and voltages
    - Sequence state
    - Recording state and elapsed time

IMPORTANT:
    This module does not access GPIO or other hardware.

    MainWindow is responsible for reading hardware
    and updating this session.

    DataLogger reads snapshots from this session.

    RPM values are measurements, NOT estimates
    calculated from PWM percentages.
"""

from __future__ import annotations

import math
import time

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import config


# ============================================================
# TEST METADATA
# ============================================================

@dataclass
class TestMetadata:
    """Metadata describing one recorded experiment."""

    test_name: str = config.DEFAULT_TEST_NAME
    mount_name: str = config.DEFAULT_MOUNT_NAME
    comment: str = config.DEFAULT_TEST_COMMENT
    date_time: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Return metadata in JSON-friendly form."""

        return {
            "test_name": self.test_name,
            "mount_name": self.mount_name,
            "comment": self.comment,
            "date_time": (
                self.date_time.isoformat()
                if self.date_time is not None
                else None
            ),
        }


# ============================================================
# TEST SESSION
# ============================================================

class TestSession:
    """
    Store the logical state of the test bench.

    Hardware controllers update this state
    through MainWindow.

    DataLogger reads snapshots from this state.
    """

    def __init__(self) -> None:

        # ----------------------------------------------------
        # Metadata
        # ----------------------------------------------------

        self.metadata = TestMetadata()

        # ----------------------------------------------------
        # Main fan
        # ----------------------------------------------------

        self.main_fan_active = (
            config.DEFAULT_MAIN_FAN_ACTIVE
        )

        self.main_fan_pwm_percent = (
            config.DEFAULT_MAIN_FAN_PWM
        )

        # Measured RPM.
        # None means no valid measurement is available.

        self.main_fan_rpm: Optional[float] = None

        # ----------------------------------------------------
        # Smoke fan
        # ----------------------------------------------------

        self.smoke_fan_active = (
            config.DEFAULT_SMOKE_FAN_ACTIVE
        )

        self.smoke_fan_pwm_percent = (
            config.DEFAULT_SMOKE_FAN_PWM
        )

        self.smoke_fan_rpm: Optional[float] = None

        # ----------------------------------------------------
        # Smoke machine
        # ----------------------------------------------------

        # Manually logged state only.
        # The Pi does not control the smoke machine.

        self.smoke_machine_active = (
            config.DEFAULT_SMOKE_MACHINE_ACTIVE
        )

        # ----------------------------------------------------
        # Optical sensors
        # ----------------------------------------------------

        self.sensor_1_active = (
            config.DEFAULT_SENSOR_1_ACTIVE
        )

        self.sensor_1_voltage_v: Optional[float] = None

        self.sensor_2_active = (
            config.DEFAULT_SENSOR_2_ACTIVE
        )

        self.sensor_2_voltage_v: Optional[float] = None

        # ----------------------------------------------------
        # Sequence
        # ----------------------------------------------------

        self.sequence_running = (
            config.DEFAULT_SEQUENCE_RUNNING
        )

        # ----------------------------------------------------
        # Recording
        # ----------------------------------------------------

        self.recording = False

        self._recording_start_monotonic: Optional[
            float
        ] = None

        self._recording_start_datetime: Optional[
            datetime
        ] = None

        self._elapsed_at_stop_s: Optional[
            float
        ] = None

    # ========================================================
    # METADATA
    # ========================================================

    def set_metadata(
        self,
        test_name: str = "",
        mount_name: str = "",
        comment: str = "",
    ) -> None:

        self.metadata.test_name = str(
            test_name
        ).strip()

        self.metadata.mount_name = str(
            mount_name
        ).strip()

        self.metadata.comment = str(
            comment
        ).strip()

    def get_metadata(self) -> TestMetadata:

        return self.metadata

    # ========================================================
    # RECORDING
    # ========================================================

    def start_recording(self) -> None:
        """
        Start a new recording timer.

        Uses a monotonic clock for elapsed time.
        """

        if self.recording:
            return

        now_monotonic = time.monotonic()
        now_datetime = datetime.now()

        self.recording = True

        self._recording_start_monotonic = (
            now_monotonic
        )

        self._recording_start_datetime = (
            now_datetime
        )

        self._elapsed_at_stop_s = None

        self.metadata.date_time = (
            now_datetime
        )

    def stop_recording(self) -> None:
        """
        Stop recording and freeze elapsed time.
        """

        if not self.recording:
            return

        if self._recording_start_monotonic is None:

            self._elapsed_at_stop_s = 0.0

        else:

            self._elapsed_at_stop_s = max(
                0.0,
                time.monotonic()
                - self._recording_start_monotonic,
            )

        self.recording = False

    def is_recording(self) -> bool:

        return self.recording

    def get_elapsed_time_s(self) -> float:

        if self.recording:

            if self._recording_start_monotonic is None:
                return 0.0

            return max(
                0.0,
                time.monotonic()
                - self._recording_start_monotonic,
            )

        if self._elapsed_at_stop_s is not None:

            return self._elapsed_at_stop_s

        return 0.0

    def get_recording_start_datetime(
        self,
    ) -> Optional[datetime]:

        return self._recording_start_datetime

    # ========================================================
    # RPM VALIDATION
    # ========================================================

    @staticmethod
    def _validate_rpm(
        rpm: Optional[float],
    ) -> Optional[float]:
        """
        Validate a measured RPM value.

        None:
            Measurement unavailable.

        0:
            No pulses measured / reported zero RPM.

        Positive number:
            Measured rotational speed.

        Negative, NaN and infinite values are rejected.

        NOTE:
            Zero pulses do not prove the fan
            is physically stopped. The FG signal
            could be disconnected.
        """

        if rpm is None:
            return None

        if isinstance(rpm, bool):
            raise TypeError(
                "RPM must be numeric or None."
            )

        value = float(rpm)

        if not math.isfinite(value):
            raise ValueError(
                "RPM must be finite."
            )

        if value < 0:
            raise ValueError(
                "RPM cannot be negative."
            )

        return value

    # ========================================================
    # MAIN FAN
    # ========================================================

    def set_main_fan_state(
        self,
        active: bool,
        pwm_percent: Optional[int] = None,
    ) -> None:
        """
        Update commanded main-fan state.

        Does not change measured RPM.
        """

        self.main_fan_active = bool(active)

        if pwm_percent is not None:

            self.main_fan_pwm_percent = int(
                pwm_percent
            )

    def set_main_fan_active(
        self,
        active: bool,
    ) -> None:

        self.main_fan_active = bool(active)

    def set_main_fan_pwm(
        self,
        pwm_percent: int,
    ) -> None:

        self.main_fan_pwm_percent = int(
            pwm_percent
        )

    def set_main_fan_rpm(
        self,
        rpm: Optional[float],
    ) -> None:
        """
        Store measured RPM from the FG monitor.
        """

        self.main_fan_rpm = self._validate_rpm(
            rpm
        )

    def get_main_fan_rpm(
        self,
    ) -> Optional[float]:

        return self.main_fan_rpm

    # ========================================================
    # SMOKE FAN
    # ========================================================

    def set_smoke_fan_state(
        self,
        active: bool,
        pwm_percent: Optional[int] = None,
    ) -> None:
        """
        Update commanded smoke-fan state.

        Does not change measured RPM.
        """

        self.smoke_fan_active = bool(active)

        if pwm_percent is not None:

            self.smoke_fan_pwm_percent = int(
                pwm_percent
            )

    def set_smoke_fan_active(
        self,
        active: bool,
    ) -> None:

        self.smoke_fan_active = bool(active)

    def set_smoke_fan_pwm(
        self,
        pwm_percent: int,
    ) -> None:

        self.smoke_fan_pwm_percent = int(
            pwm_percent
        )

    def set_smoke_fan_rpm(
        self,
        rpm: Optional[float],
    ) -> None:
        """
        Store measured RPM from the FG monitor.
        """

        self.smoke_fan_rpm = self._validate_rpm(
            rpm
        )

    def get_smoke_fan_rpm(
        self,
    ) -> Optional[float]:

        return self.smoke_fan_rpm

    # ========================================================
    # SMOKE MACHINE
    # ========================================================

    def set_smoke_machine_active(
        self,
        active: bool,
    ) -> None:
        """
        Update manually logged smoke-machine state.

        Does not control physical hardware.
        """

        self.smoke_machine_active = bool(
            active
        )

    # ========================================================
    # SENSOR 1
    # ========================================================

    def set_sensor_1_active(
        self,
        active: bool,
    ) -> None:

        self.sensor_1_active = bool(active)

        if not self.sensor_1_active:

            self.sensor_1_voltage_v = None

    def set_sensor_1_voltage(
        self,
        voltage_v: Optional[float],
    ) -> None:

        if not self.sensor_1_active:

            self.sensor_1_voltage_v = None
            return

        self.sensor_1_voltage_v = (
            None
            if voltage_v is None
            else float(voltage_v)
        )

    # ========================================================
    # SENSOR 2
    # ========================================================

    def set_sensor_2_active(
        self,
        active: bool,
    ) -> None:

        self.sensor_2_active = bool(active)

        if not self.sensor_2_active:

            self.sensor_2_voltage_v = None

    def set_sensor_2_voltage(
        self,
        voltage_v: Optional[float],
    ) -> None:

        if not self.sensor_2_active:

            self.sensor_2_voltage_v = None
            return

        self.sensor_2_voltage_v = (
            None
            if voltage_v is None
            else float(voltage_v)
        )

    # ========================================================
    # SEQUENCE
    # ========================================================

    def set_sequence_running(
        self,
        running: bool,
    ) -> None:

        self.sequence_running = bool(
            running
        )

    # ========================================================
    # STOP ALL LOGICAL STATE
    # ========================================================

    def apply_stop_all_state(self) -> None:
        """
        Reset commanded fan and sequence states.

        Recording remains active.

        Sensor states are unchanged.
        Smoke-machine state is unchanged.

        IMPORTANT:
            This does NOT physically stop hardware.
            MainWindow must command the controllers.

            Physical fan power cut-off is required.
        """

        self.main_fan_active = False
        self.main_fan_pwm_percent = 0

        self.smoke_fan_active = False
        self.smoke_fan_pwm_percent = 0

        self.sequence_running = False

        # RPM values are deliberately NOT forced to zero.
        #
        # They represent measurements.
        # The actual fan may still be spinning.

    # ========================================================
    # DATA SNAPSHOT
    # ========================================================

    def get_data_snapshot(self) -> dict:
        """
        Return a complete time-series sample.

        The snapshot contains existing CSV values
        plus measured RPM for both fans.

        DataLogger selects columns using
        config.CSV_COLUMNS.

        RPM will appear in the CSV after the
        config file is updated accordingly.
        """

        return {
            "timestamp": datetime.now().strftime(
                config.TIMESTAMP_FORMAT
            ),

            "elapsed_time_s": (
                self.get_elapsed_time_s()
            ),

            "main_fan_active": (
                self.main_fan_active
            ),

            "main_fan_pwm_percent": (
                self.main_fan_pwm_percent
            ),

            "main_fan_rpm": (
                self.main_fan_rpm
            ),

            "smoke_fan_active": (
                self.smoke_fan_active
            ),

            "smoke_fan_pwm_percent": (
                self.smoke_fan_pwm_percent
            ),

            "smoke_fan_rpm": (
                self.smoke_fan_rpm
            ),

            "smoke_machine_active": (
                self.smoke_machine_active
            ),

            "sensor_1_active": (
                self.sensor_1_active
            ),

            "sensor_1_voltage_v": (
                self.sensor_1_voltage_v
            ),

            "sensor_2_active": (
                self.sensor_2_active
            ),

            "sensor_2_voltage_v": (
                self.sensor_2_voltage_v
            ),

            "sequence_running": (
                self.sequence_running
            ),
        }