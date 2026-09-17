"""
hardware/sensors.py

Optical sensor controller for the AGCO Airflow Smoke Test Bench.

Hardware:
    - 2 x OPT101 optical sensors
    - 1 x ADS1115 ADC
    - 2 x permanently powered red LEDs

Connections:
    Sensor 1 -> ADS1115 A0
    Sensor 2 -> ADS1115 A1

The LEDs are powered externally by 12 V.
They are NOT controlled by Raspberry Pi GPIO.

Enabling a sensor means that its ADC measurements
are enabled in software.

Disabling a sensor means that its measurements
return None.

The physical LED remains powered whenever
the external 12 V supply is enabled.
"""

from __future__ import annotations

from typing import Optional

from hardware.adc import ADCController
from hardware.leds import LEDController


class OpticalSensor:
    """
    Represents one optical measurement position.

    Each sensor consists of:
        - OPT101 photodiode sensor
        - ADS1115 analog input
        - Corresponding red LED

    The LEDController is retained for compatibility
    with the existing application.

    Its state is logical only.
    """

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(
        self,
        adc: ADCController,
        adc_channel: int,
        led: LEDController,
        name: str,
    ) -> None:

        if not isinstance(adc, ADCController):
            raise TypeError(
                "adc must be an ADCController instance."
            )

        if (
            isinstance(adc_channel, bool)
            or not isinstance(adc_channel, int)
        ):
            raise TypeError(
                "ADC channel must be an integer."
            )

        if adc_channel not in (0, 1, 2, 3):
            raise ValueError(
                "ADC channel must be 0, 1, 2 or 3."
            )

        if not isinstance(led, LEDController):
            raise TypeError(
                "led must be an LEDController instance."
            )

        self.adc = adc
        self.adc_channel = adc_channel
        self.led = led
        self.name = name

        # Measurement starts disabled.
        self._active = False

        # Reset logical LED request.
        # This does not physically turn off the LED.
        self.led.off()

    # ========================================================
    # ENABLE / DISABLE
    # ========================================================

    def enable(self) -> None:
        """
        Enable sensor measurements.

        The physical LED is not affected.
        """

        self.led.on()

        self._active = True

    def disable(self) -> None:
        """
        Disable sensor measurements.

        The physical LED is not affected.
        """

        self.led.off()

        self._active = False

    def set_active(
        self,
        active: bool,
    ) -> None:
        """
        Enable or disable measurements.
        """

        if not isinstance(active, bool):
            raise TypeError(
                "Sensor active state must be a boolean."
            )

        if active:
            self.enable()
        else:
            self.disable()

    # ========================================================
    # SENSOR STATE
    # ========================================================

    def is_active(self) -> bool:
        """
        Return whether measurements are enabled.

        This does not indicate the physical LED state.
        """

        return self._active

    # ========================================================
    # VOLTAGE MEASUREMENT
    # ========================================================

    def read_voltage(self) -> Optional[float]:
        """
        Read the OPT101 output voltage.

        Returns:
            float:
                Measured voltage in volts.

            None:
                Sensor measurements are disabled.

        The ADCController handles the actual
        ADS1115 communication.
        """

        if not self._active:
            return None

        return self.adc.read_voltage(
            self.adc_channel
        )

    # ========================================================
    # RAW ADC MEASUREMENT
    # ========================================================

    def read_raw(self) -> Optional[int]:
        """
        Read the raw ADS1115 conversion value.

        Intended for debugging and calibration.

        Returns None when measurements are disabled.
        """

        if not self._active:
            return None

        return self.adc.read_raw(
            self.adc_channel
        )

    # ========================================================
    # CLEANUP
    # ========================================================

    def cleanup(self) -> None:
        """
        Disable sensor measurements.

        The ADC is shared between both sensors,
        so it is not closed here.

        The physical LED is not switched off.
        """

        self.disable()