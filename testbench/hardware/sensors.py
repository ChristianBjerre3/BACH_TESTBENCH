"""
hardware/sensors.py

Optical sensor control for the airflow/smoke test bench.

This module combines:
    - One OPT101 optical sensor
    - One ADS1115 ADC channel
    - One corresponding red LED

The OpticalSensor class represents one complete optical measurement
position in the test bench.

When a sensor is enabled:
    - Its corresponding LED is turned ON
    - Voltage measurements are allowed

When a sensor is disabled:
    - Its corresponding LED is turned OFF
    - Voltage measurements return None

The ADCController is shared between both optical sensors.
"""

from __future__ import annotations

from typing import Optional

from hardware.adc import ADCController
from hardware.leds import LEDController


class OpticalSensor:
    """
    Represents one complete optical measurement position.

    Each optical sensor consists of:
        - One OPT101
        - One ADS1115 input channel
        - One red LED

    The LED automatically follows the active state of the sensor.
    """

    def __init__(
        self,
        adc: ADCController,
        adc_channel: int,
        led: LEDController,
        name: str,
    ) -> None:
        """
        Initialize an optical sensor.

        Parameters
        ----------
        adc:
            Shared ADCController instance.

        adc_channel:
            ADS1115 input channel used by this sensor.

        led:
            LEDController belonging to this sensor.

        name:
            Human-readable sensor name.
        """

        if not isinstance(adc, ADCController):
            raise TypeError("adc must be an ADCController instance.")

        if not isinstance(adc_channel, int):
            raise TypeError("adc_channel must be an integer.")

        if adc_channel not in (0, 1, 2, 3):
            raise ValueError(
                f"ADC channel must be 0, 1, 2 or 3. "
                f"Received: {adc_channel}"
            )

        if not isinstance(led, LEDController):
            raise TypeError("led must be an LEDController instance.")

        self.adc = adc
        self.adc_channel = adc_channel
        self.led = led
        self.name = name

        self._active = False

        # Safety: sensor LEDs must always start OFF.
        self.led.off()

    def enable(self) -> None:
        """
        Enable the optical sensor.

        The corresponding LED is automatically turned ON.
        """

        self.led.on()
        self._active = True

    def disable(self) -> None:
        """
        Disable the optical sensor.

        The corresponding LED is automatically turned OFF.
        """

        self.led.off()
        self._active = False

    def set_active(self, active: bool) -> None:
        """
        Set the sensor state directly.

        Parameters
        ----------
        active:
            True:
                Enable sensor and turn LED ON.

            False:
                Disable sensor and turn LED OFF.
        """

        if not isinstance(active, bool):
            raise TypeError("Sensor active state must be a boolean.")

        if active:
            self.enable()
        else:
            self.disable()

    def is_active(self) -> bool:
        """
        Return True if the sensor is currently enabled.
        """

        return self._active

    def read_voltage(self) -> Optional[float]:
        """
        Read the current OPT101 output voltage.

        Returns
        -------
        float or None
            Measured voltage in volts when the sensor is active.

            None when the sensor is disabled.
        """

        if not self._active:
            return None

        return self.adc.read_voltage(self.adc_channel)

    def read_raw(self) -> Optional[int]:
        """
        Read the raw ADS1115 value.

        Mainly intended for debugging and future calibration.

        Returns
        -------
        int or None
            Raw ADC value when active.

            None when disabled.
        """

        if not self._active:
            return None

        return self.adc.read_raw(self.adc_channel)

    def cleanup(self) -> None:
        """
        Safely disable the sensor.

        The ADC is NOT closed here because the ADCController is shared
        between both optical sensors.
        """

        self.disable()