"""
hardware/fans.py

Fan controller for the AGCO Airflow Smoke Test Bench.

Hardware:
    Raspberry Pi 4
    Delta EFB0412VHD-SP05
    4-wire BLDC fans

Fan connections:
    Red    -> +12 V
    Black  -> GND
    Blue   -> FG feedback
    Yellow -> PWM input

PWM control:
    GPIO -> 4.7k resistor -> 2N3704 base
    2N3704 collector -> fan PWM input
    2N3704 emitter -> GND

The transistor INVERTS the GPIO signal.

    GPIO HIGH -> transistor ON  -> fan PWM LOW
    GPIO LOW  -> transistor OFF -> fan PWM HIGH

IMPORTANT:
    The fan can run at maximum speed if its PWM
    input is disconnected or the Raspberry Pi
    stops driving the GPIO.

    Software cannot guarantee a safe OFF state.

    A physical 12 V power cut-off must be available.
"""

from __future__ import annotations

from dataclasses import dataclass

from gpiozero import PWMOutputDevice

import config


# ============================================================
# FAN STATE
# ============================================================

@dataclass
class FanState:
    """
    Represents the requested software state.

    active:
        True if the fan has been commanded ON.

    pwm_percent:
        Requested fan PWM duty cycle, 0-100 %.
    """

    active: bool = False
    pwm_percent: int = 0


# ============================================================
# FAN CONTROLLER
# ============================================================

class FanController:
    """
    Control one Delta 4-wire fan.

    The fan receives constant external 12 V.

    The Raspberry Pi controls only the separate
    PWM input through an inverting transistor.

    Example:

        fan = FanController(
            gpio_pin=config.MAIN_FAN_PWM_GPIO,
            name="Main Fan",
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

        self.gpio_pin = gpio_pin
        self.name = name

        self.pwm_frequency_hz = pwm_frequency_hz

        self.state = FanState()

        self._closed = False

        # The transistor inverts GPIO PWM.
        self._inverted = config.FAN_PWM_INVERTED

        # GPIO HIGH = transistor ON = fan PWM LOW.
        #
        # Initialize with the fan commanded OFF.
        #
        # WARNING:
        # This only works while the GPIO is
        # actively driven by the Raspberry Pi.

        initial_gpio_value = (
            1.0 if self._inverted else 0.0
        )

        self._device = PWMOutputDevice(
            pin=self.gpio_pin,
            active_high=True,
            initial_value=initial_gpio_value,
            frequency=self.pwm_frequency_hz,
        )

    # ========================================================
    # INTERNAL HELPERS
    # ========================================================

    def _ensure_open(self) -> None:
        """
        Prevent commands after GPIO cleanup.
        """

        if self._closed:
            raise RuntimeError(
                f"{self.name}: controller is closed."
            )

    def _gpio_duty_from_fan_duty(
        self,
        fan_duty: float,
    ) -> float:
        """
        Convert requested fan PWM to GPIO PWM.

        fan_duty:
            0.0 = fan STOP
            1.0 = fan maximum PWM

        The transistor inverts the signal.
        """

        if self._inverted:
            return 1.0 - fan_duty

        return fan_duty

    def _apply_output(self) -> None:
        """
        Apply the requested fan state.

        The output is inverted to compensate
        for the transistor stage.
        """

        self._ensure_open()

        # OFF always overrides the stored PWM.
        if not self.state.active:
            fan_duty = 0.0

        else:
            fan_duty = (
                self.state.pwm_percent / 100.0
            )

        gpio_duty = self._gpio_duty_from_fan_duty(
            fan_duty
        )

        self._device.value = gpio_duty

    # ========================================================
    # PUBLIC CONTROL
    # ========================================================

    def on(self) -> None:
        """
        Enable the fan.

        The previously selected PWM percentage
        is used.

        If PWM is 0 %, the fan remains commanded
        to stop.
        """

        self._ensure_open()

        self.state.active = True

        self._apply_output()

    def off(self) -> None:
        """
        Command the fan to stop.

        The selected PWM percentage is preserved.
        """

        self._ensure_open()

        self.state.active = False

        self._apply_output()

    def set_pwm(
        self,
        pwm_percent: int,
    ) -> None:
        """
        Set the requested fan PWM percentage.

        Allowed values are defined in config.py.

        Example:
            0, 10, 20, ..., 100
        """

        self._ensure_open()

        if (
            isinstance(pwm_percent, bool)
            or not isinstance(pwm_percent, int)
        ):
            raise TypeError(
                "PWM percentage must be an integer."
            )

        if pwm_percent not in config.PWM_LEVELS:
            raise ValueError(
                f"PWM must be one of "
                f"{config.PWM_LEVELS}. "
                f"Received: {pwm_percent}"
            )

        self.state.pwm_percent = pwm_percent

        # Only update the physical output if ON.
        if self.state.active:
            self._apply_output()

    def stop(self) -> None:
        """
        STOP ALL behaviour.

        Command fan OFF and reset PWM to 0 %.
        """

        self._ensure_open()

        self.state.active = False
        self.state.pwm_percent = 0

        self._apply_output()

    # ========================================================
    # STATE INFORMATION
    # ========================================================

    def get_state(self) -> FanState:
        """
        Return a copy of the current state.
        """

        return FanState(
            active=self.state.active,
            pwm_percent=self.state.pwm_percent,
        )

    def is_active(self) -> bool:
        """
        Return the commanded active state.
        """

        return self.state.active

    def get_pwm(self) -> int:
        """
        Return the selected PWM percentage.
        """

        return self.state.pwm_percent

    # ========================================================
    # CLEANUP
    # ========================================================

    def cleanup(self) -> None:
        """
        Release the GPIO resource.

        First commands the fan to stop.

        WARNING:
        GPIO release can leave the PWM input
        floating/high, causing maximum fan speed.

        Disconnect the fan's 12 V supply before
        shutting down the Raspberry Pi.
        """

        if self._closed:
            return

        self.state.active = False
        self.state.pwm_percent = 0

        try:
            # Best-effort software STOP.
            self._apply_output()

        finally:
            self._closed = True

            # Releasing GPIO is NOT a
            # guaranteed physical fan stop.
            self._device.close()