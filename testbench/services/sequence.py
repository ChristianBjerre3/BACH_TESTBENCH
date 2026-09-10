"""
services/sequence.py

Non-blocking sequence controller for the airflow/smoke test bench.

The controller executes timed steps for:
    - Main fan ON/OFF
    - Main fan PWM
    - Smoke fan ON/OFF
    - Smoke fan PWM

The controller does NOT:
    - Sleep or block the GUI
    - Control recording
    - Control optical sensors
    - Control the smoke machine
    - Write log files

MainWindow owns the higher-level workflow.

MainWindow should call update() regularly, normally from the existing
10 Hz GUI/update timer.
"""

from __future__ import annotations

import time

from dataclasses import dataclass
from typing import Optional, Sequence

import config

from services.test_session import TestSession


# ====================================================================
# SEQUENCE STEP
# ====================================================================


@dataclass(frozen=True)
class SequenceStep:
    """One timed fan-control step."""

    duration_s: float

    main_fan_active: bool
    main_fan_pwm_percent: int

    smoke_fan_active: bool
    smoke_fan_pwm_percent: int

    def __post_init__(self) -> None:
        """Validate sequence-step values."""

        duration = float(
            self.duration_s
        )

        if duration < config.MIN_SEQUENCE_STEP_DURATION_S:
            raise ValueError(
                "Sequence step duration must be at least "
                f"{config.MIN_SEQUENCE_STEP_DURATION_S} s."
            )

        if not isinstance(
            self.main_fan_active,
            bool,
        ):
            raise TypeError(
                "main_fan_active must be bool."
            )

        if not isinstance(
            self.smoke_fan_active,
            bool,
        ):
            raise TypeError(
                "smoke_fan_active must be bool."
            )

        if self.main_fan_pwm_percent not in config.PWM_LEVELS:
            raise ValueError(
                "Invalid main fan PWM value: "
                f"{self.main_fan_pwm_percent}. "
                f"Allowed values: {config.PWM_LEVELS}"
            )

        if self.smoke_fan_pwm_percent not in config.PWM_LEVELS:
            raise ValueError(
                "Invalid smoke fan PWM value: "
                f"{self.smoke_fan_pwm_percent}. "
                f"Allowed values: {config.PWM_LEVELS}"
            )


# ====================================================================
# SEQUENCE CONTROLLER
# ====================================================================


class SequenceController:
    """
    Execute a list of SequenceStep objects without blocking.

    Fan objects are intentionally accepted by interface/duck typing.

    This is important because the same controller must work with:
        - hardware.fans.FanController
        - simulation.fans.FanController

    Expected fan interface:
        set_pwm(percent)
        on()
        off()
        stop()
    """

    def __init__(
        self,
        main_fan,
        smoke_fan,
        session: TestSession,
    ) -> None:
        """Initialize controller."""

        self.main_fan = main_fan
        self.smoke_fan = smoke_fan
        self.session = session

        self._steps: list[SequenceStep] = []

        self._running = False

        self._current_step_index: Optional[int] = None

        # Absolute monotonic deadline for the current step.
        #
        # Using deadlines instead of resetting the start time to "now"
        # prevents small GUI/update delays from accumulating over the
        # whole sequence.
        self._step_deadline: Optional[float] = None

    # =================================================================
    # SEQUENCE CONFIGURATION
    # =================================================================

    def set_steps(
        self,
        steps: Sequence[SequenceStep],
    ) -> None:
        """
        Replace the current sequence.

        A running sequence cannot be modified.
        """

        if self._running:
            raise RuntimeError(
                "Cannot change sequence while it is running."
            )

        validated_steps = []

        for step in steps:

            if not isinstance(
                step,
                SequenceStep,
            ):
                raise TypeError(
                    "All sequence entries must be SequenceStep objects."
                )

            validated_steps.append(
                step
            )

        self._steps = validated_steps

    def add_step(
        self,
        step: SequenceStep,
    ) -> None:
        """Append one step."""

        if self._running:
            raise RuntimeError(
                "Cannot add a step while sequence is running."
            )

        if not isinstance(
            step,
            SequenceStep,
        ):
            raise TypeError(
                "step must be a SequenceStep."
            )

        self._steps.append(
            step
        )

    def clear_steps(self) -> None:
        """Remove all configured steps."""

        if self._running:
            raise RuntimeError(
                "Cannot clear sequence while it is running."
            )

        self._steps.clear()

        self._current_step_index = None
        self._step_deadline = None

    def get_steps(
        self,
    ) -> list[SequenceStep]:
        """Return a copy of configured sequence steps."""

        return list(
            self._steps
        )

    # =================================================================
    # START
    # =================================================================

    def start(self) -> None:
        """
        Start sequence execution.

        The first step is applied immediately.

        Raises RuntimeError if:
            - sequence is already running
            - no steps have been configured
        """

        if self._running:
            raise RuntimeError(
                "Sequence is already running."
            )

        if not self._steps:
            raise RuntimeError(
                "Cannot start an empty sequence."
            )

        self._running = True
        self._current_step_index = 0

        start_time = time.monotonic()

        first_step = self._steps[0]

        self._step_deadline = (
            start_time
            + first_step.duration_s
        )

        self.session.set_sequence_running(
            True
        )

        self._apply_step(
            first_step
        )

    # =================================================================
    # UPDATE
    # =================================================================

    def update(self) -> None:
        """
        Advance the sequence when step deadlines are reached.

        This method is non-blocking.

        MainWindow should call it regularly.

        IMPORTANT:
        A while-loop is used intentionally.

        If the GUI/update loop is delayed long enough to pass more than
        one step boundary, update() catches up to the correct point in
        the sequence rather than adding that delay to every later step.
        """

        if not self._running:
            return

        if self._current_step_index is None:
            return

        if self._step_deadline is None:
            return

        now = time.monotonic()

        while (
            self._running
            and self._step_deadline is not None
            and now >= self._step_deadline
        ):

            next_index = (
                self._current_step_index + 1
            )

            # --------------------------------------------------------
            # Sequence complete
            # --------------------------------------------------------

            if next_index >= len(
                self._steps
            ):

                self._finish_sequence()
                return

            # --------------------------------------------------------
            # Advance to next step
            # --------------------------------------------------------

            self._current_step_index = (
                next_index
            )

            next_step = self._steps[
                self._current_step_index
            ]

            # Critical timing detail:
            #
            # Add the next duration to the PREVIOUS deadline.
            #
            # Do NOT use:
            #
            #     time.monotonic() + duration
            #
            # because that would accumulate GUI/update delay.
            self._step_deadline = (
                self._step_deadline
                + next_step.duration_s
            )

            self._apply_step(
                next_step
            )

            # The while-loop checks the same captured "now" again.
            #
            # If the program is already beyond this new deadline,
            # another step is advanced immediately.

    # =================================================================
    # MANUAL STOP
    # =================================================================

    def stop(self) -> None:
        """
        Stop a running sequence.

        Fans are placed in the safe stopped state:
            - Main fan OFF / PWM 0
            - Smoke fan OFF / PWM 0

        Recording is intentionally NOT handled here.
        MainWindow owns recording workflow/ownership.
        """

        self._stop_outputs()

        self._running = False
        self._current_step_index = None
        self._step_deadline = None

        self.session.set_sequence_running(
            False
        )

    # =================================================================
    # NORMAL COMPLETION
    # =================================================================

    def _finish_sequence(self) -> None:
        """
        Finish a sequence after the final step expires.

        This is separate from MainWindow's higher-level completion
        handling.

        MainWindow can detect:

            running -> stopped

        and then:
            - log sequence_completed
            - stop sequence-owned recording
            - unlock manual controls
        """

        self._stop_outputs()

        self._running = False
        self._current_step_index = None
        self._step_deadline = None

        self.session.set_sequence_running(
            False
        )

    # =================================================================
    # APPLY STEP
    # =================================================================

    def _apply_step(
        self,
        step: SequenceStep,
    ) -> None:
        """
        Apply one sequence step to both fan controllers and TestSession.
        """

        # ------------------------------------------------------------
        # Main fan
        # ------------------------------------------------------------

        self.main_fan.set_pwm(
            step.main_fan_pwm_percent
        )

        if step.main_fan_active:
            self.main_fan.on()
        else:
            self.main_fan.off()

        self.session.set_main_fan_state(
            active=step.main_fan_active,
            pwm_percent=step.main_fan_pwm_percent,
        )

        # ------------------------------------------------------------
        # Smoke fan
        # ------------------------------------------------------------

        self.smoke_fan.set_pwm(
            step.smoke_fan_pwm_percent
        )

        if step.smoke_fan_active:
            self.smoke_fan.on()
        else:
            self.smoke_fan.off()

        self.session.set_smoke_fan_state(
            active=step.smoke_fan_active,
            pwm_percent=step.smoke_fan_pwm_percent,
        )

    # =================================================================
    # STOP OUTPUTS
    # =================================================================

    def _stop_outputs(self) -> None:
        """
        Put both fan outputs into explicit OFF / PWM 0 state.
        """

        self.main_fan.stop()
        self.smoke_fan.stop()

        self.session.set_main_fan_state(
            active=False,
            pwm_percent=0,
        )

        self.session.set_smoke_fan_state(
            active=False,
            pwm_percent=0,
        )

    # =================================================================
    # STATUS
    # =================================================================

    def is_running(self) -> bool:
        """Return whether a sequence is currently running."""

        return self._running

    def get_current_step_index(
        self,
    ) -> Optional[int]:
        """
        Return zero-based current step index.

        Returns None when no sequence is running.
        """

        if not self._running:
            return None

        return self._current_step_index

    def get_current_step_number(
        self,
    ) -> Optional[int]:
        """
        Return human-readable one-based current step number.

        Example:
            first step -> 1

        Returns None when sequence is not running.
        """

        index = (
            self.get_current_step_index()
        )

        if index is None:
            return None

        return index + 1

    def get_current_step(
        self,
    ) -> Optional[SequenceStep]:
        """Return current SequenceStep or None."""

        index = (
            self.get_current_step_index()
        )

        if index is None:
            return None

        if index >= len(
            self._steps
        ):
            return None

        return self._steps[
            index
        ]

    def get_step_count(self) -> int:
        """Return number of configured steps."""

        return len(
            self._steps
        )

    def get_total_duration_s(self) -> float:
        """Return configured total sequence duration."""

        return sum(
            step.duration_s
            for step in self._steps
        )

    def get_remaining_step_time_s(
        self,
    ) -> Optional[float]:
        """
        Return approximate remaining time in current step.

        Primarily useful for GUI/status display.
        """

        if (
            not self._running
            or self._step_deadline is None
        ):
            return None

        return max(
            0.0,
            self._step_deadline
            - time.monotonic(),
        )

    # =================================================================
    # CLEANUP
    # =================================================================

    def cleanup(self) -> None:
        """
        Safely stop the sequence/controller during application shutdown.
        """

        self.stop()