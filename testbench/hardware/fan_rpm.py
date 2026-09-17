"""
hardware/fan_rpm.py

RPM measurement for the AGCO Airflow Smoke Test Bench.

Hardware:
    Raspberry Pi 4
    Delta EFB0412VHD-SP05 fans

Connections:
    Fan 1 FG -> GPIO17
    Fan 2 FG -> GPIO27

The FG outputs are open-collector signals.

The schematic provides external 10k pull-up
resistors to 3.3 V.

According to the Delta datasheet:
    4 FG periods = 1 revolution.

RPM calculation:
    RPM = pulses_per_second * 60 / 4

IMPORTANT:
    This is an initial GPIO callback implementation.
    Its accuracy must be validated on real hardware.
"""

from __future__ import annotations

import time

from collections import deque
from threading import Lock
from typing import Optional

from gpiozero import DigitalInputDevice


# ============================================================
# FAN RPM MONITOR
# ============================================================

class FanRPMMonitor:
    """
    Measure fan RPM by counting rising FG edges.

    The fan has its own PWM controller.

    This class only reads the FG signal.
    It does not control fan speed or power.
    """

    def __init__(
        self,
        gpio_pin: int,
        name: str,
        pulses_per_revolution: int = 4,
        measurement_window_s: float = 1.0,
    ) -> None:

        if pulses_per_revolution <= 0:
            raise ValueError(
                "pulses_per_revolution must be positive."
            )

        if measurement_window_s <= 0:
            raise ValueError(
                "measurement_window_s must be positive."
            )

        self.gpio_pin = gpio_pin
        self.name = name

        self.pulses_per_revolution = (
            pulses_per_revolution
        )

        self.measurement_window_s = (
            measurement_window_s
        )

        self._lock = Lock()

        # Store timestamps of recent rising edges.
        self._pulse_times = deque()

        self._started_at = time.monotonic()

        self._closed = False

        # External 3.3 V pull-up is provided
        # by the electrical schematic.
        #
        # Therefore GPIOZero must not enable
        # an internal pull-up or pull-down.

        self._input = DigitalInputDevice(
            pin=self.gpio_pin,
            pull_up=None,
            active_state=True,
            bounce_time=None,
        )

        # Count rising edges.
        self._input.when_activated = (
            self._on_pulse
        )

    # ========================================================
    # INTERNAL PULSE HANDLING
    # ========================================================

    def _on_pulse(self) -> None:
        """
        Called when the FG signal goes HIGH.

        Only store a timestamp here.

        Do not perform calculations or GUI updates
        inside the GPIO callback.
        """

        now = time.monotonic()

        with self._lock:

            if self._closed:
                return

            self._pulse_times.append(now)

            self._remove_old_pulses(now)

    def _remove_old_pulses(
        self,
        now: float,
    ) -> None:
        """
        Remove timestamps outside the
        measurement window.

        Must be called while holding self._lock.
        """

        cutoff = (
            now - self.measurement_window_s
        )

        while (
            self._pulse_times
            and self._pulse_times[0] < cutoff
        ):
            self._pulse_times.popleft()

    # ========================================================
    # RPM MEASUREMENT
    # ========================================================

    def get_rpm(self) -> Optional[float]:
        """
        Return the measured RPM.

        Returns:
            None:
                The monitor is closed or
                the first measurement window
                has not finished.

            float:
                Calculated RPM.

        Note:
            0 RPM means no pulses were observed
            during the measurement window.

            It does not prove that the fan is
            physically stopped. A disconnected
            FG wire can produce the same result.
        """

        now = time.monotonic()

        with self._lock:

            if self._closed:
                return None

            elapsed = (
                now - self._started_at
            )

            # Wait for the first complete window.
            if elapsed < self.measurement_window_s:
                return None

            self._remove_old_pulses(now)

            pulse_count = len(
                self._pulse_times
            )

        pulses_per_second = (
            pulse_count
            / self.measurement_window_s
        )

        revolutions_per_second = (
            pulses_per_second
            / self.pulses_per_revolution
        )

        rpm = revolutions_per_second * 60.0

        return round(rpm, 1)

    # ========================================================
    # STATE
    # ========================================================

    def is_available(self) -> bool:
        """
        Return whether the GPIO monitor is open.

        This does not confirm that a fan
        or FG wire is physically connected.
        """

        return not self._closed

    # ========================================================
    # CLEANUP
    # ========================================================

    def cleanup(self) -> None:
        """
        Stop monitoring the FG input.

        Does not affect fan power or PWM.
        """

        with self._lock:

            if self._closed:
                return

            self._closed = True

        self._input.when_activated = None

        self._input.close()

        with self._lock:
            self._pulse_times.clear()