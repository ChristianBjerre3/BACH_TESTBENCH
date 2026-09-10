"""
simulation/fans.py

Simulated fan control for desktop testing without Raspberry Pi hardware.

Mirrors the public interface of hardware.fans.FanController but stores
state in memory only. Does not import gpiozero or any GPIO library.
"""

from __future__ import annotations

from dataclasses import dataclass

import config


@dataclass
class FanState:
    """
    Represents the current software state of a simulated fan.

    Compatible with MainWindow usage of hardware.fans.FanState
    (active + pwm_percent fields).
    """

    active: bool = False
    pwm_percent: int = 0


class FanController:
    """
    Simulated 2-wire BLDC fan controller.

    Behaves like hardware.fans.FanController regarding:
        - on() / off() / set_pwm() / stop()
        - PWM validation against config.PWM_LEVELS
        - off() preserves selected PWM
        - stop() sets active=False and PWM=0
        - active=True with PWM=0 is allowed
    """

    def __init__(
        self,
        gpio_pin: int,
        name: str,
        pwm_frequency_hz: int = config.FAN_PWM_FREQUENCY_HZ,
    ) -> None:
        self.gpio_pin = gpio_pin
        self.name = name
        self.pwm_frequency_hz = pwm_frequency_hz

        self.state = FanState()

    def on(self) -> None:
        """Turn the fan ON using the currently selected PWM value."""
        self.state.active = True

    def off(self) -> None:
        """
        Turn the fan OFF.

        The selected PWM percentage is preserved.
        """
        self.state.active = False

    def set_pwm(self, pwm_percent: int) -> None:
        """
        Set requested fan PWM duty cycle.

        Raises
        ------
        TypeError:
            If pwm_percent is not an integer.
        ValueError:
            If pwm_percent is outside config.PWM_LEVELS.
        """
        if not isinstance(pwm_percent, int):
            raise TypeError("PWM percentage must be an integer.")

        if pwm_percent not in config.PWM_LEVELS:
            raise ValueError(
                f"PWM percentage must be one of {config.PWM_LEVELS}. "
                f"Received: {pwm_percent}"
            )

        self.state.pwm_percent = pwm_percent

    def stop(self) -> None:
        """Immediately stop the fan and reset PWM to 0 % (STOP ALL)."""
        self.state.active = False
        self.state.pwm_percent = 0

    def get_state(self) -> FanState:
        """Return a copy of the current fan state."""
        return FanState(
            active=self.state.active,
            pwm_percent=self.state.pwm_percent,
        )

    def is_active(self) -> bool:
        """Return True if the fan is currently commanded ON."""
        return self.state.active

    def get_pwm(self) -> int:
        """Return the currently selected PWM percentage."""
        return self.state.pwm_percent

    def cleanup(self) -> None:
        """Reset simulated fan state."""
        self.state.active = False
        self.state.pwm_percent = 0
