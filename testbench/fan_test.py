"""
Minimal one-fan hardware test.

This file intentionally does NOT start the full GUI application.
It exercises only the current fan controller implementation so you can
verify the real Raspberry Pi GPIO/PWM setup in isolation.

Run from the project directory:
    python fan_test.py
"""

from __future__ import annotations

import time

import config
from hardware.fans import FanController


def main() -> None:
    """Run a small test sequence on the main fan only."""
    fan = FanController(
        gpio_pin=config.MAIN_FAN_PWM_GPIO,
        name="Main Fan",
    )

    print(f"Testing main fan on GPIO {config.MAIN_FAN_PWM_GPIO}")

    try:
        for pwm in (0, 25, 50, 75, 100):
            fan.set_pwm(pwm)
            fan.on()
            print(f"PWM = {pwm}% -> fan ON")
            time.sleep(1.5)

            fan.off()
            print("fan OFF")
            time.sleep(0.5)

        fan.stop()
        print("STOP ALL executed")

    except Exception as exc:
        print(f"Fan test failed: {exc}")
        raise

    finally:
        try:
            fan.cleanup()
            print("GPIO cleaned up")
        except Exception as cleanup_error:
            print(f"Cleanup warning: {cleanup_error}")


if __name__ == "__main__":
    main()
