"""
hardware/leds.py

LED interface for the AGCO Airflow Smoke Test Bench.

Hardware:
    2 x TLDR5800 red LEDs

According to the AGCO schematic, the LEDs are
powered directly from the external 12 V supply
through individual 680 ohm resistors.

The Raspberry Pi does NOT control the LEDs.

This class preserves the interface expected by
the existing OpticalSensor and MainWindow classes.

IMPORTANT:
    on() and off() only update the requested
    software state.

    They do NOT physically switch the LEDs.

    Actual LED operation depends on the
    external 12 V power supply.
"""

from __future__ import annotations

import config


class LEDController:
    """
    Compatibility interface for a hardwired LED.

    No GPIO device is created.

    The constructor retains gpio_pin so that
    existing MainWindow code remains compatible.
    """

    def __init__(
        self,
        gpio_pin: int,
        name: str,
    ) -> None:

        self.gpio_pin = gpio_pin
        self.name = name

        self._requested_active = False
        self._closed = False

        self._hardwired = config.LEDS_HARDWIRED

        if not self._hardwired:
            raise RuntimeError(
                f"{self.name}: This LED controller "
                "requires LEDS_HARDWIRED = True."
            )

    # ========================================================
    # INTERNAL VALIDATION
    # ========================================================

    def _ensure_open(self) -> None:
        """
        Prevent commands after cleanup.
        """

        if self._closed:
            raise RuntimeError(
                f"{self.name}: LED controller is closed."
            )

    # ========================================================
    # LED INTERFACE
    # ========================================================

    def on(self) -> None:
        """
        Store a software ON request.

        Does not physically switch the LED.
        """

        self._ensure_open()

        self._requested_active = True

    def off(self) -> None:
        """
        Store a software OFF request.

        Does not physically switch the LED.
        """

        self._ensure_open()

        self._requested_active = False

    def set_active(
        self,
        active: bool,
    ) -> None:
        """
        Update the requested software state.
        """

        self._ensure_open()

        if not isinstance(active, bool):
            raise TypeError(
                "LED active state must be a boolean."
            )

        if active:
            self.on()
        else:
            self.off()

    # ========================================================
    # STATE
    # ========================================================

    def is_active(self) -> bool:
        """
        Return the requested software state.

        WARNING:
        This is NOT a measurement of whether
        the physical LED is illuminated.
        """

        return self._requested_active

    def is_hardwired(self) -> bool:
        """
        Return whether the LED uses fixed wiring.
        """

        return self._hardwired

    # ========================================================
    # CLEANUP
    # ========================================================

    def cleanup(self) -> None:
        """
        Release the software interface.

        No GPIO resources exist.

        This cannot turn off the physical LED.
        """

        if self._closed:
            return

        self._requested_active = False
        self._closed = True