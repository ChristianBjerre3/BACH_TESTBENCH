"""
hardware/leds.py

LED control module for the airflow/smoke test bench.

This module provides a small reusable LEDController class for the
two red LEDs used together with the OPT101 optical sensors.

Each LED is controlled digitally from a Raspberry Pi GPIO pin.

GPIO numbering:
    BCM

Important:
- Each LED must be connected with an appropriate series resistor.
- The Raspberry Pi GPIO pin must not be connected directly across
  an LED without current limiting.
"""

from __future__ import annotations

from gpiozero import DigitalOutputDevice


class LEDController:
    """
    Controls one LED connected to a Raspberry Pi GPIO pin.

    Example:
        led = LEDController(
            gpio_pin=23,
            name="Sensor 1 LED"
        )

        led.on()
        led.off()
        led.cleanup()
    """

    def __init__(
        self,
        gpio_pin: int,
        name: str,
    ) -> None:
        """
        Initialize the LED controller.

        Parameters
        ----------
        gpio_pin:
            BCM GPIO pin controlling the LED.

        name:
            Human-readable LED name used for debugging/logging.
        """

        self.gpio_pin = gpio_pin
        self.name = name

        self._active = False

        self._device = DigitalOutputDevice(
            pin=self.gpio_pin,
            active_high=True,
            initial_value=False,
        )

    def on(self) -> None:
        """
        Turn the LED ON.
        """

        self._device.on()
        self._active = True

    def off(self) -> None:
        """
        Turn the LED OFF.
        """

        self._device.off()
        self._active = False

    def set_active(self, active: bool) -> None:
        """
        Set LED state directly.

        Parameters
        ----------
        active:
            True  -> LED ON
            False -> LED OFF
        """

        if not isinstance(active, bool):
            raise TypeError("LED active state must be a boolean.")

        if active:
            self.on()
        else:
            self.off()

    def is_active(self) -> bool:
        """
        Return True if the LED is currently ON.
        """

        return self._active

    def cleanup(self) -> None:
        """
        Turn the LED OFF and release the GPIO resource.
        """

        self._device.off()
        self._active = False
        self._device.close()