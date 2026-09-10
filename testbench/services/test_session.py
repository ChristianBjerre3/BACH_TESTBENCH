"""
services/test_session.py

Central logical state for the airflow/smoke test bench.

This module stores the current experiment state independently of the
physical hardware and GUI.

It keeps track of:
    - Test metadata
    - Fan states and PWM
    - Smoke-machine logged state
    - Optical sensor states and latest voltages
    - Sequence state
    - Recording state
    - Recording elapsed time

The recording timer uses time.monotonic() so elapsed time is not affected
by changes to the system clock.
"""

from __future__ import annotations

import time

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import config


# ====================================================================
# TEST METADATA
# ====================================================================


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


# ====================================================================
# TEST SESSION
# ====================================================================


class TestSession:
    """
    Store the current logical state of the test bench.

    Hardware controllers update this state through MainWindow.
    DataLogger reads snapshots from this state.

    This class does not directly access hardware or GUI objects.
    """

    def __init__(self) -> None:
        """Initialize the test bench in its safe/default state."""

        # ------------------------------------------------------------
        # Metadata
        # ------------------------------------------------------------

        self.metadata = TestMetadata()

        # ------------------------------------------------------------
        # Main fan
        # ------------------------------------------------------------

        self.main_fan_active = (
            config.DEFAULT_MAIN_FAN_ACTIVE
        )

        self.main_fan_pwm_percent = (
            config.DEFAULT_MAIN_FAN_PWM
        )

        # ------------------------------------------------------------
        # Smoke fan
        # ------------------------------------------------------------

        self.smoke_fan_active = (
            config.DEFAULT_SMOKE_FAN_ACTIVE
        )

        self.smoke_fan_pwm_percent = (
            config.DEFAULT_SMOKE_FAN_PWM
        )

        # ------------------------------------------------------------
        # Smoke machine
        #
        # This is a manually logged state only.
        # The Pi does not physically control the smoke machine.
        # ------------------------------------------------------------

        self.smoke_machine_active = (
            config.DEFAULT_SMOKE_MACHINE_ACTIVE
        )

        # ------------------------------------------------------------
        # Optical sensors
        # ------------------------------------------------------------

        self.sensor_1_active = (
            config.DEFAULT_SENSOR_1_ACTIVE
        )

        self.sensor_1_voltage_v: Optional[float] = None

        self.sensor_2_active = (
            config.DEFAULT_SENSOR_2_ACTIVE
        )

        self.sensor_2_voltage_v: Optional[float] = None

        # ------------------------------------------------------------
        # Sequence
        # ------------------------------------------------------------

        self.sequence_running = (
            config.DEFAULT_SEQUENCE_RUNNING
        )

        # ------------------------------------------------------------
        # Recording
        # ------------------------------------------------------------

        self.recording = False

        self._recording_start_monotonic: Optional[float] = None
        self._recording_start_datetime: Optional[datetime] = None

        # Stores the final duration after recording stops.
        #
        # This allows get_elapsed_time_s() to freeze at the final
        # duration instead of continuing to increase after Stop.
        self._elapsed_at_stop_s: Optional[float] = None

    # =================================================================
    # METADATA
    # =================================================================

    def set_metadata(
        self,
        test_name: str = "",
        mount_name: str = "",
        comment: str = "",
    ) -> None:
        """Set metadata for the next/current experiment."""

        self.metadata.test_name = str(test_name).strip()
        self.metadata.mount_name = str(mount_name).strip()
        self.metadata.comment = str(comment).strip()

    def get_metadata(self) -> TestMetadata:
        """Return current metadata."""

        return self.metadata

    # =================================================================
    # RECORDING
    # =================================================================

    def start_recording(self) -> None:
        """
        Start a new recording timer.

        Every new recording:
            - resets elapsed time to zero
            - stores a new wall-clock date/time
            - starts a new monotonic timer
        """

        if self.recording:
            return

        now_monotonic = time.monotonic()
        now_datetime = datetime.now()

        self.recording = True

        self._recording_start_monotonic = now_monotonic
        self._recording_start_datetime = now_datetime

        # New recording -> previous frozen duration is discarded.
        self._elapsed_at_stop_s = None

        # Recording start time is also experiment date/time.
        self.metadata.date_time = now_datetime

    def stop_recording(self) -> None:
        """
        Stop recording and freeze the final elapsed duration.

        Calling this while not recording is harmless.
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
        """Return whether recording is currently active."""

        return self.recording

    def get_elapsed_time_s(self) -> float:
        """
        Return recording elapsed time in seconds.

        Behaviour:

        Before first recording:
            0.0

        During recording:
            continuously increasing

        After recording stops:
            frozen at final recording duration

        When a new recording starts:
            reset to approximately 0.0
        """

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
        """Return wall-clock start time of the current/latest recording."""

        return self._recording_start_datetime

    # =================================================================
    # MAIN FAN
    # =================================================================

    def set_main_fan_state(
        self,
        active: bool,
        pwm_percent: Optional[int] = None,
    ) -> None:
        """Update logical main-fan state."""

        self.main_fan_active = bool(active)

        if pwm_percent is not None:
            self.main_fan_pwm_percent = int(
                pwm_percent
            )

    def set_main_fan_active(
        self,
        active: bool,
    ) -> None:
        """Update only main-fan ON/OFF state."""

        self.main_fan_active = bool(active)

    def set_main_fan_pwm(
        self,
        pwm_percent: int,
    ) -> None:
        """Update only main-fan PWM."""

        self.main_fan_pwm_percent = int(
            pwm_percent
        )

    # =================================================================
    # SMOKE FAN
    # =================================================================

    def set_smoke_fan_state(
        self,
        active: bool,
        pwm_percent: Optional[int] = None,
    ) -> None:
        """Update logical smoke-fan state."""

        self.smoke_fan_active = bool(active)

        if pwm_percent is not None:
            self.smoke_fan_pwm_percent = int(
                pwm_percent
            )

    def set_smoke_fan_active(
        self,
        active: bool,
    ) -> None:
        """Update only smoke-fan ON/OFF state."""

        self.smoke_fan_active = bool(active)

    def set_smoke_fan_pwm(
        self,
        pwm_percent: int,
    ) -> None:
        """Update only smoke-fan PWM."""

        self.smoke_fan_pwm_percent = int(
            pwm_percent
        )

    # =================================================================
    # SMOKE MACHINE
    # =================================================================

    def set_smoke_machine_active(
        self,
        active: bool,
    ) -> None:
        """
        Update manually logged smoke-machine state.

        This does not control physical hardware.
        """

        self.smoke_machine_active = bool(active)

    # =================================================================
    # SENSOR 1
    # =================================================================

    def set_sensor_1_active(
        self,
        active: bool,
    ) -> None:
        """Update Sensor 1 logical state."""

        self.sensor_1_active = bool(active)

        if not self.sensor_1_active:
            self.sensor_1_voltage_v = None

    def set_sensor_1_voltage(
        self,
        voltage_v: Optional[float],
    ) -> None:
        """Store latest Sensor 1 voltage."""

        if not self.sensor_1_active:
            self.sensor_1_voltage_v = None
            return

        self.sensor_1_voltage_v = (
            None
            if voltage_v is None
            else float(voltage_v)
        )

    # =================================================================
    # SENSOR 2
    # =================================================================

    def set_sensor_2_active(
        self,
        active: bool,
    ) -> None:
        """Update Sensor 2 logical state."""

        self.sensor_2_active = bool(active)

        if not self.sensor_2_active:
            self.sensor_2_voltage_v = None

    def set_sensor_2_voltage(
        self,
        voltage_v: Optional[float],
    ) -> None:
        """Store latest Sensor 2 voltage."""

        if not self.sensor_2_active:
            self.sensor_2_voltage_v = None
            return

        self.sensor_2_voltage_v = (
            None
            if voltage_v is None
            else float(voltage_v)
        )

    # =================================================================
    # SEQUENCE
    # =================================================================

    def set_sequence_running(
        self,
        running: bool,
    ) -> None:
        """Update logical sequence-running state."""

        self.sequence_running = bool(
            running
        )

    # =================================================================
    # STOP ALL LOGICAL STATE
    # =================================================================

    def apply_stop_all_state(self) -> None:
        """
        Apply the logical fan/sequence part of STOP ALL.

        IMPORTANT:
        Recording ownership is handled by MainWindow.

        Therefore this method intentionally does NOT:
            - stop recording
            - change sensor states
            - change smoke-machine state
        """

        self.main_fan_active = False
        self.main_fan_pwm_percent = 0

        self.smoke_fan_active = False
        self.smoke_fan_pwm_percent = 0

        self.sequence_running = False

    # =================================================================
    # DATA SNAPSHOT
    # =================================================================

    def get_data_snapshot(self) -> dict:
        """
        Return one complete time-series sample.

        The returned keys match config.CSV_COLUMNS.
        """

        return {
            "timestamp": datetime.now().strftime(
                config.TIMESTAMP_FORMAT
            ),

            "elapsed_time_s": self.get_elapsed_time_s(),

            "main_fan_active": self.main_fan_active,
            "main_fan_pwm_percent": self.main_fan_pwm_percent,

            "smoke_fan_active": self.smoke_fan_active,
            "smoke_fan_pwm_percent": self.smoke_fan_pwm_percent,

            "smoke_machine_active": self.smoke_machine_active,

            "sensor_1_active": self.sensor_1_active,
            "sensor_1_voltage_v": self.sensor_1_voltage_v,

            "sensor_2_active": self.sensor_2_active,
            "sensor_2_voltage_v": self.sensor_2_voltage_v,

            "sequence_running": self.sequence_running,
        }