"""
simulation/sensors.py

Simulated optical sensor for desktop testing without Raspberry Pi hardware.

Mirrors the public interface and enable/LED coupling of
hardware.sensors.OpticalSensor.

Does not import hardware/ packages and does not use isinstance checks
against hardware classes.
"""

from __future__ import annotations

from typing import Any, Optional


class OpticalSensor:
    """
    Simulated OPT101 + LED measurement position.

    Sensor ON:
        corresponding LED ON, measurements enabled

    Sensor OFF:
        corresponding LED OFF, read_voltage/read_raw return None
    """

    def __init__(
        self,
        adc: Any,
        adc_channel: int,
        led: Any,
        name: str,
    ) -> None:
        if not hasattr(adc, "read_voltage") or not hasattr(adc, "read_raw"):
            raise TypeError(
                "adc must provide read_voltage() and read_raw() methods."
            )

        if not isinstance(adc_channel, int):
            raise TypeError("adc_channel must be an integer.")

        if adc_channel not in (0, 1, 2, 3):
            raise ValueError(
                f"ADC channel must be 0, 1, 2 or 3. "
                f"Received: {adc_channel}"
            )

        if not hasattr(led, "on") or not hasattr(led, "off"):
            raise TypeError(
                "led must provide on() and off() methods."
            )

        self.adc = adc
        self.adc_channel = adc_channel
        self.led = led
        self.name = name

        self._active = False

        # Safety: sensor LEDs must always start OFF.
        self.led.off()

    def enable(self) -> None:
        """Enable the optical sensor and turn its LED ON."""
        self.led.on()
        self._active = True

    def disable(self) -> None:
        """Disable the optical sensor and turn its LED OFF."""
        self.led.off()
        self._active = False

    def set_active(self, active: bool) -> None:
        """
        Set the sensor state directly.

        Raises
        ------
        TypeError:
            If active is not a boolean.
        """
        if not isinstance(active, bool):
            raise TypeError("Sensor active state must be a boolean.")

        if active:
            self.enable()
        else:
            self.disable()

    def is_active(self) -> bool:
        """Return True if the sensor is currently enabled."""
        return self._active

    def read_voltage(self) -> Optional[float]:
        """
        Read the current simulated OPT101 voltage.

        Returns None when the sensor is disabled.
        """
        if not self._active:
            return None

        return self.adc.read_voltage(self.adc_channel)

    def read_raw(self) -> Optional[int]:
        """
        Read the simulated raw ADC value.

        Returns None when the sensor is disabled.
        """
        if not self._active:
            return None

        return self.adc.read_raw(self.adc_channel)

    def cleanup(self) -> None:
        """Safely disable the sensor (does not close shared ADC)."""
        self.disable()
