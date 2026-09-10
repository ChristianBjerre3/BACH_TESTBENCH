"""
hardware/adc.py

ADS1115 interface for the airflow/smoke test bench.

This module provides an ADCController class used to read analog
voltages from the ADS1115 connected to the Raspberry Pi through I2C.

The ADS1115 is used because the Raspberry Pi does not have native
analog inputs.

Current channel usage:
    A0 -> OPT101 sensor 1
    A1 -> OPT101 sensor 2

GPIO numbering:
    BCM

I2C pins on Raspberry Pi 4:
    GPIO2 -> SDA
    GPIO3 -> SCL
"""

from __future__ import annotations

import board
import busio

from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

import config


class ADCController:
    """
    Interface to the ADS1115 ADC.

    This class initializes the I2C connection and ADS1115 once and
    provides simple methods for reading analog input voltages.

    Example:
        adc = ADCController()

        voltage_1 = adc.read_voltage(0)
        voltage_2 = adc.read_voltage(1)
    """

    def __init__(self) -> None:
        """
        Initialize Raspberry Pi I2C and the ADS1115.
        """

        self._i2c = busio.I2C(
            board.SCL,
            board.SDA,
        )

        self._ads = ADS1115(
            self._i2c,
            address=config.ADS1115_I2C_ADDRESS,
        )

        self._ads.gain = config.ADS1115_GAIN

        self._channels = {
            0: AnalogIn(self._ads, 0),
            1: AnalogIn(self._ads, 1),
            2: AnalogIn(self._ads, 2),
            3: AnalogIn(self._ads, 3),
        }

    def read_voltage(self, channel: int) -> float:
        """
        Read voltage from one ADS1115 input channel.

        Parameters
        ----------
        channel:
            ADS1115 channel number.

            Valid values:
                0 -> A0
                1 -> A1
                2 -> A2
                3 -> A3

        Returns
        -------
        float
            Measured voltage in volts.

        Raises
        ------
        TypeError:
            If channel is not an integer.

        ValueError:
            If channel is outside the valid range 0-3.
        """

        if not isinstance(channel, int):
            raise TypeError("ADC channel must be an integer.")

        if channel not in self._channels:
            raise ValueError(
                f"ADC channel must be one of {tuple(self._channels.keys())}. "
                f"Received: {channel}"
            )

        return float(self._channels[channel].voltage)

    def read_raw(self, channel: int) -> int:
        """
        Read the raw ADC value from one ADS1115 input channel.

        This is not required for normal operation, but is useful for
        debugging and later calibration work.

        Parameters
        ----------
        channel:
            ADS1115 channel number from 0 to 3.

        Returns
        -------
        int
            Raw ADC conversion value.
        """

        if not isinstance(channel, int):
            raise TypeError("ADC channel must be an integer.")

        if channel not in self._channels:
            raise ValueError(
                f"ADC channel must be one of {tuple(self._channels.keys())}. "
                f"Received: {channel}"
            )

        return int(self._channels[channel].value)

    def close(self) -> None:
        """
        Release the I2C resource.

        The ADS1115 itself does not require a shutdown command, but
        deinitializing I2C is useful when the application exits.
        """

        if self._i2c is not None:
            self._i2c.deinit()
            self._i2c = None