"""
simulation/adc.py

Simulated ADS1115 ADC for desktop testing without I2C hardware.

Mirrors the public interface of hardware.adc.ADCController.
Does not import board, busio or adafruit ADS1115 libraries.

Channel 0 and channel 1 produce slowly varying, slightly different
voltage signals with a small amount of random noise for live plots.
"""

from __future__ import annotations

import math
import random
import time


# Approximate ADS1115 full-scale at gain = 1 (+/- 4.096 V).
_ADS1115_FS_VOLTAGE = 4.096
_ADS1115_MAX_RAW = 32767


class ADCController:
    """
    Simulated multi-channel ADC.

    Each channel has a smooth sinusoidal base signal plus light noise.
    """

    def __init__(self) -> None:
        self._start_time = time.monotonic()
        self._closed = False

        # Channel-specific signal parameters (phase / rate / amplitude).
        self._channel_params = {
            0: {
                "offset": 1.55,
                "amplitude": 0.35,
                "freq_hz": 0.08,
                "phase": 0.0,
            },
            1: {
                "offset": 1.75,
                "amplitude": 0.28,
                "freq_hz": 0.11,
                "phase": 1.3,
            },
            2: {
                "offset": 1.20,
                "amplitude": 0.20,
                "freq_hz": 0.05,
                "phase": 0.7,
            },
            3: {
                "offset": 1.40,
                "amplitude": 0.22,
                "freq_hz": 0.06,
                "phase": 2.1,
            },
        }

    def read_voltage(self, channel: int) -> float:
        """
        Read a simulated voltage from one ADC channel.

        Raises
        ------
        TypeError:
            If channel is not an integer.
        ValueError:
            If channel is outside 0-3, or the simulator is closed.
        """
        self._ensure_open()
        self._validate_channel(channel)

        params = self._channel_params[channel]
        t = time.monotonic() - self._start_time

        base = params["offset"] + params["amplitude"] * math.sin(
            2.0 * math.pi * params["freq_hz"] * t + params["phase"]
        )

        # Slow secondary drift so plots are not a pure sine.
        drift = 0.05 * math.sin(2.0 * math.pi * 0.02 * t + channel)

        noise = random.uniform(-0.015, 0.015)

        voltage = base + drift + noise

        # Keep values in a realistic positive OPT101-like range.
        voltage = max(0.05, min(3.30, voltage))

        return float(voltage)

    def read_raw(self, channel: int) -> int:
        """
        Return a raw ADC-like integer derived from the simulated voltage.
        """
        voltage = self.read_voltage(channel)
        raw = int(round((voltage / _ADS1115_FS_VOLTAGE) * _ADS1115_MAX_RAW))
        return max(0, min(_ADS1115_MAX_RAW, raw))

    def close(self) -> None:
        """Mark the simulated ADC as closed."""
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise ValueError("Simulated ADC has been closed.")

    @staticmethod
    def _validate_channel(channel: int) -> None:
        if not isinstance(channel, int):
            raise TypeError("ADC channel must be an integer.")

        if channel not in (0, 1, 2, 3):
            raise ValueError(
                f"ADC channel must be one of (0, 1, 2, 3). "
                f"Received: {channel}"
            )
