"""
simulation/leds.py

Simulated LED control for desktop testing without Raspberry Pi hardware.

Mirrors the public interface of hardware.leds.LEDController.
Does not import gpiozero or any GPIO library.
"""

from __future__ import annotations


class LEDController:
    """Simulated LED that stores ON/OFF state in memory only."""

    def __init__(
        self,
        gpio_pin: int,
        name: str,
    ) -> None:
        self.gpio_pin = gpio_pin
        self.name = name
        self._active = False

    def on(self) -> None:
        """Turn the LED ON."""
        self._active = True

    def off(self) -> None:
        """Turn the LED OFF."""
        self._active = False

    def set_active(self, active: bool) -> None:
        """
        Set LED state directly.

        Raises
        ------
        TypeError:
            If active is not a boolean.
        """
        if not isinstance(active, bool):
            raise TypeError("LED active state must be a boolean.")

        if active:
            self.on()
        else:
            self.off()

    def is_active(self) -> bool:
        """Return True if the LED is currently ON."""
        return self._active

    def cleanup(self) -> None:
        """Turn the LED OFF."""
        self._active = False
