"""
hardware/fans.py

Fan control module for the airflow/smoke test bench.

This module provides a reusable FanController class for controlling
a 2-wire 12 V BLDC fan through a MOSFET using PWM from a Raspberry Pi.

Important:
- The Raspberry Pi GPIO pin does NOT power the fan directly.
- The GPIO pin only controls the MOSFET gate.
- The fan is powered from an external 12 V supply.
- Raspberry Pi GND and 12 V supply GND must be common.

GPIO numbering:
    BCM

The class is designed so the same implementation can be used for:
    - Main airflow fan
    - Smoke chamber fan
"""

from __future__ import annotations

from dataclasses import dataclass

from gpiozero import PWMOutputDevice

import config


@dataclass
class FanState:
    """
    Represents the current software state of a fan.

    active:
        True when the fan is commanded ON.

    pwm_percent:
        Requested PWM duty cycle in percent, from 0 to 100.
    """

    active: bool = False
    pwm_percent: int = 0


class FanController:
    """
    Controls one 2-wire BLDC fan through a MOSFET.

    The fan is controlled using supply-side PWM.

    Example:
        fan = FanController(
            gpio_pin=config.MAIN_FAN_PWM_GPIO,
            name="Main Fan"
        )

        fan.set_pwm(50)
        fan.on()

        fan.off()
        fan.cleanup()
    """

    def __init__(
        self,
        gpio_pin: int,
        name: str,
        pwm_frequency_hz: int = config.FAN_PWM_FREQUENCY_HZ,
    ) -> None:
        """
        Initialize the fan controller.

        Parameters
        ----------
        gpio_pin:
            BCM GPIO pin connected to the MOSFET gate.

        name:
            Human-readable fan name used for debugging and logging.

        pwm_frequency_hz:
            PWM frequency used for fan control.
        """

        self.gpio_pin = gpio_pin
        self.name = name
        self.pwm_frequency_hz = pwm_frequency_hz

        self.state = FanState()

        self._device = PWMOutputDevice(
            pin=self.gpio_pin,
            active_high=True,
            initial_value=0.0,
            frequency=self.pwm_frequency_hz,
        )

    def on(self) -> None:
        """
        Turn the fan ON using the currently selected PWM value.

        If the stored PWM value is 0 %, the fan remains physically stopped,
        but the software state is still set to active.

        Normally the GUI should avoid this situation by setting a useful
        PWM value before turning the fan on.
        """

        self.state.active = True
        self._apply_output()

    def off(self) -> None:
        """
        Turn the fan OFF.

        The selected PWM percentage is preserved internally so the fan can
        later be turned back on at the same requested PWM value.
        """

        self.state.active = False
        self._apply_output()

    def set_pwm(self, pwm_percent: int) -> None:
        """
        Set requested fan PWM duty cycle.

        Parameters
        ----------
        pwm_percent:
            PWM duty cycle in percent.

            Allowed values are currently:
                0, 10, 20, ..., 100

        Raises
        ------
        TypeError:
            If pwm_percent is not an integer.

        ValueError:
            If pwm_percent is outside the allowed PWM values.
        """

        if not isinstance(pwm_percent, int):
            raise TypeError("PWM percentage must be an integer.")

        if pwm_percent not in config.PWM_LEVELS:
            raise ValueError(
                f"PWM percentage must be one of {config.PWM_LEVELS}. "
                f"Received: {pwm_percent}"
            )

        self.state.pwm_percent = pwm_percent

        if self.state.active:
            self._apply_output()

    def stop(self) -> None:
        """
        Immediately stop the fan and reset PWM to 0 %.

        This is intended for STOP ALL behaviour.
        """

        self.state.active = False
        self.state.pwm_percent = 0
        self._apply_output()

    def get_state(self) -> FanState:
        """
        Return a copy of the current fan state.

        Returning a copy prevents external code from modifying the
        internal fan state directly.
        """

        return FanState(
            active=self.state.active,
            pwm_percent=self.state.pwm_percent,
        )

    def is_active(self) -> bool:
        """
        Return True if the fan is currently commanded ON.
        """

        return self.state.active

    def get_pwm(self) -> int:
        """
        Return the currently selected PWM percentage.
        """

        return self.state.pwm_percent

    def cleanup(self) -> None:
        """
        Safely shut down the fan controller and release the GPIO resource.

        This should be called when the application closes.
        """

        self.state.active = False
        self.state.pwm_percent = 0

        self._device.value = 0.0
        self._device.close()

    def _apply_output(self) -> None:
        """
        Apply the current software state to the physical PWM output.

        GPIOZero expects PWM duty cycle as a floating-point value:

            0.0 = 0 %
            0.5 = 50 %
            1.0 = 100 %
        """

        if not self.state.active:
            self._device.value = 0.0
            return

        duty_cycle = self.state.pwm_percent / 100.0
        self._device.value = duty_cycle