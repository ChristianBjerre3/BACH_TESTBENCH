"""
gui/main_window.py

Main application window for the airflow/smoke test bench.

MainWindow is the central coordinator between:

GUI
    - ControlTab
    - LiveTab
    - SequenceTab
    - LiveStatusPanel

Hardware / simulation
    - Main fan
    - Smoke fan
    - ADC
    - Optical sensors
    - LEDs

Services
    - TestSession
    - DataLogger
    - SequenceController

MainWindow owns the higher-level workflow, including:
    - Manual recording
    - Sequence-owned recording
    - Recording ownership
    - Sequence completion handling
    - Event logging
    - STOP ALL semantics
    - Sensor selection for sequences
    - Smoke-machine state synchronization
    - Live plot timebase
"""

from __future__ import annotations

import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QMessageBox,
    QWidget,
    QHBoxLayout,
    QSplitter,
)

import config

from services.test_session import TestSession
from services.logger import DataLogger
from services.sequence import (
    SequenceController,
    SequenceStep,
)

from gui.control_tab import ControlTab
from gui.live_tab import LiveTab
from gui.sequence_tab import SequenceTab
from gui.live_status_panel import LiveStatusPanel


# ====================================================================
# HARDWARE BACKEND
# ====================================================================


def _load_hardware_backend():
    """
    Import the correct hardware backend.

    Raspberry Pi libraries are only imported in real mode.
    This allows the complete GUI to run on Windows in simulation mode.
    """

    mode = config.HARDWARE_MODE

    if mode not in config.VALID_HARDWARE_MODES:
        raise ValueError(
            f"Invalid HARDWARE_MODE={mode!r}. "
            f"Allowed values: {config.VALID_HARDWARE_MODES}."
        )

    if mode == "real":

        from hardware.fans import FanController
        from hardware.adc import ADCController
        from hardware.leds import LEDController
        from hardware.sensors import OpticalSensor

    else:

        from simulation.fans import FanController
        from simulation.adc import ADCController
        from simulation.leds import LEDController
        from simulation.sensors import OpticalSensor

    return (
        FanController,
        ADCController,
        LEDController,
        OpticalSensor,
    )


# ====================================================================
# MAIN WINDOW
# ====================================================================


class MainWindow(QMainWindow):
    """Main test-bench application window."""

    def __init__(self) -> None:
        """Initialize complete application."""

        super().__init__()

        # ------------------------------------------------------------
        # Window
        # ------------------------------------------------------------

        mode_label = (
            "SIMULATION"
            if config.HARDWARE_MODE == "simulation"
            else "REAL HARDWARE"
        )

        self.setWindowTitle(
            f"{config.APP_NAME} - "
            f"v{config.APP_VERSION} "
            f"[{mode_label}]"
        )

        self.resize(
            1100,
            800,
        )

        self._cleanup_done = False

        # ------------------------------------------------------------
        # Live graph timebase
        #
        # This is deliberately independent of recording time.
        # ------------------------------------------------------------

        self._live_start_monotonic = (
            time.monotonic()
        )

        # ------------------------------------------------------------
        # Recording ownership
        #
        # False:
        #     no recording, or recording started manually.
        #
        # True:
        #     recording was automatically started by a sequence.
        # ------------------------------------------------------------

        self._recording_started_by_sequence = False

        # ------------------------------------------------------------
        # Application state
        # ------------------------------------------------------------

        self.session = TestSession()

        # ------------------------------------------------------------
        # Hardware / simulation
        # ------------------------------------------------------------

        self._initialize_hardware()

        # ------------------------------------------------------------
        # Services
        # ------------------------------------------------------------

        self.logger = DataLogger(
            session=self.session
        )

        self.sequence = SequenceController(
            main_fan=self.main_fan,
            smoke_fan=self.smoke_fan,
            session=self.session,
        )

        # ------------------------------------------------------------
        # Event-state snapshot
        #
        # Used to detect fan/sensor/smoke state changes consistently,
        # including changes caused automatically by sequence steps.
        # ------------------------------------------------------------

        self._last_event_state = (
            self._get_event_state_snapshot()
        )

        # ------------------------------------------------------------
        # GUI
        # ------------------------------------------------------------

        self._build_ui()
        self._connect_signals()

        # ------------------------------------------------------------
        # Timer
        # ------------------------------------------------------------

        self._create_update_timer()

        # ------------------------------------------------------------
        # Initial GUI synchronization
        # ------------------------------------------------------------

        self._update_gui()

    # =================================================================
    # HARDWARE INITIALIZATION
    # =================================================================

    def _initialize_hardware(self) -> None:
        """Initialize real or simulated hardware."""

        (
            FanController,
            ADCController,
            LEDController,
            OpticalSensor,
        ) = _load_hardware_backend()

        # ------------------------------------------------------------
        # Fans
        # ------------------------------------------------------------

        self.main_fan = FanController(
            gpio_pin=config.MAIN_FAN_PWM_GPIO,
            name="Main Fan",
        )

        self.smoke_fan = FanController(
            gpio_pin=config.SMOKE_FAN_PWM_GPIO,
            name="Smoke Fan",
        )

        # ------------------------------------------------------------
        # ADC
        # ------------------------------------------------------------

        self.adc = ADCController()

        # ------------------------------------------------------------
        # LEDs
        # ------------------------------------------------------------

        self.sensor_1_led = LEDController(
            gpio_pin=config.SENSOR_1_LED_GPIO,
            name="Sensor 1 LED",
        )

        self.sensor_2_led = LEDController(
            gpio_pin=config.SENSOR_2_LED_GPIO,
            name="Sensor 2 LED",
        )

        # ------------------------------------------------------------
        # Optical sensors
        # ------------------------------------------------------------

        self.sensor_1 = OpticalSensor(
            adc=self.adc,
            adc_channel=config.SENSOR_1_ADC_CHANNEL,
            led=self.sensor_1_led,
            name="Sensor 1",
        )

        self.sensor_2 = OpticalSensor(
            adc=self.adc,
            adc_channel=config.SENSOR_2_ADC_CHANNEL,
            led=self.sensor_2_led,
            name="Sensor 2",
        )

    # =================================================================
    # GUI
    # =================================================================

    def _build_ui(self) -> None:
        """Build main tab interface."""

        self.tabs = QTabWidget()

        self.control_tab = ControlTab()
        self.live_tab = LiveTab()
        self.sequence_tab = SequenceTab()

        self.control_live_panel = LiveStatusPanel()
        self.sequence_live_panel = LiveStatusPanel()

        # ------------------------------------------------------------
        # CONTROL
        # ------------------------------------------------------------

        self.tabs.addTab(
            self._wrap_with_live_panel(
                self.control_tab,
                self.control_live_panel,
            ),
            "CONTROL",
        )

        # ------------------------------------------------------------
        # LIVE DATA
        # ------------------------------------------------------------

        self.tabs.addTab(
            self.live_tab,
            "LIVE DATA",
        )

        # ------------------------------------------------------------
        # SEQUENCE
        # ------------------------------------------------------------

        self.tabs.addTab(
            self._wrap_with_live_panel(
                self.sequence_tab,
                self.sequence_live_panel,
            ),
            "SEQUENCE",
        )

        self.setCentralWidget(
            self.tabs
        )

    @staticmethod
    def _wrap_with_live_panel(
        left_widget: QWidget,
        live_panel: LiveStatusPanel,
    ) -> QWidget:
        """Place primary tab beside compact live panel."""

        container = QWidget()

        layout = QHBoxLayout(
            container
        )

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(
            0
        )

        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        splitter.addWidget(
            left_widget
        )

        splitter.addWidget(
            live_panel
        )

        splitter.setStretchFactor(
            0,
            3,
        )

        splitter.setStretchFactor(
            1,
            1,
        )

        splitter.setChildrenCollapsible(
            False
        )

        layout.addWidget(
            splitter
        )

        return container

    # =================================================================
    # SIGNALS
    # =================================================================

    def _connect_signals(self) -> None:
        """Connect GUI signals to MainWindow handlers."""

        # ------------------------------------------------------------
        # Main fan
        # ------------------------------------------------------------

        self.control_tab.main_fan_active_changed.connect(
            self._set_main_fan_active
        )

        self.control_tab.main_fan_pwm_changed.connect(
            self._set_main_fan_pwm
        )

        # ------------------------------------------------------------
        # Smoke fan
        # ------------------------------------------------------------

        self.control_tab.smoke_fan_active_changed.connect(
            self._set_smoke_fan_active
        )

        self.control_tab.smoke_fan_pwm_changed.connect(
            self._set_smoke_fan_pwm
        )

        # ------------------------------------------------------------
        # Sensors
        # ------------------------------------------------------------

        self.control_tab.sensor_1_active_changed.connect(
            self._set_sensor_1_active
        )

        self.control_tab.sensor_2_active_changed.connect(
            self._set_sensor_2_active
        )

        # ------------------------------------------------------------
        # Smoke machine
        #
        # CONTROL and SEQUENCE control the same logical state.
        # ------------------------------------------------------------

        self.control_tab.smoke_machine_active_changed.connect(
            self._set_smoke_machine_active
        )

        self.sequence_tab.smoke_machine_active_changed.connect(
            self._set_smoke_machine_active
        )

        # ------------------------------------------------------------
        # Manual recording
        # ------------------------------------------------------------

        self.control_tab.start_recording_requested.connect(
            self._start_recording
        )

        self.control_tab.stop_recording_requested.connect(
            self._stop_recording
        )

        # ------------------------------------------------------------
        # STOP ALL
        # ------------------------------------------------------------

        self.control_tab.stop_all_requested.connect(
            self._stop_all
        )

        # ------------------------------------------------------------
        # Sequence
        # ------------------------------------------------------------

        self.sequence_tab.run_sequence_requested.connect(
            self._start_sequence
        )

        self.sequence_tab.stop_sequence_requested.connect(
            self._stop_sequence
        )

    # =================================================================
    # TIMER
    # =================================================================

    def _create_update_timer(self) -> None:
        """Create central 10 Hz application timer."""

        interval_ms = max(
            1,
            int(
                config.SENSOR_SAMPLE_INTERVAL_S
                * 1000
            ),
        )

        self.update_timer = QTimer(
            self
        )

        self.update_timer.setInterval(
            interval_ms
        )

        self.update_timer.timeout.connect(
            self._update_loop
        )

        self.update_timer.start()

    # =================================================================
    # CENTRAL UPDATE LOOP
    # =================================================================

    def _update_loop(self) -> None:
        """
        Central periodic update.

        Order is important:

            1. Update sequence
            2. Detect automatic sequence completion
            3. Detect sequence-driven state changes
            4. Read sensors once
            5. Log one time-series sample
            6. Update GUI
            7. Update all plots from the same sensor sample
        """

        try:

            # --------------------------------------------------------
            # Sequence update
            # --------------------------------------------------------

            sequence_was_running = (
                self.sequence.is_running()
            )

            self.sequence.update()

            sequence_is_running = (
                self.sequence.is_running()
            )

            # Sequence steps can change fan state directly.
            self._log_state_change_events()

            # --------------------------------------------------------
            # Normal sequence completion
            # --------------------------------------------------------

            if (
                sequence_was_running
                and not sequence_is_running
            ):
                self._handle_sequence_completed()

            # --------------------------------------------------------
            # Read sensors exactly once
            # --------------------------------------------------------

            sensor_1_voltage = (
                self.sensor_1.read_voltage()
            )

            sensor_2_voltage = (
                self.sensor_2.read_voltage()
            )

            # --------------------------------------------------------
            # Store latest measurements
            # --------------------------------------------------------

            self.session.set_sensor_1_voltage(
                sensor_1_voltage
            )

            self.session.set_sensor_2_voltage(
                sensor_2_voltage
            )

            # --------------------------------------------------------
            # Time-series recording
            # --------------------------------------------------------

            if self.logger.is_recording():

                self.logger.log_sample()

            # --------------------------------------------------------
            # GUI state
            # --------------------------------------------------------

            self._update_gui()

            # --------------------------------------------------------
            # Independent live-plot time
            # --------------------------------------------------------

            live_time_s = (
                time.monotonic()
                - self._live_start_monotonic
            )

            # Existing LiveTab currently names this argument
            # elapsed_time_s, but we deliberately supply LIVE time.
            self.live_tab.add_plot_sample(
                elapsed_time_s=live_time_s,
                sensor_1_voltage=sensor_1_voltage,
                sensor_2_voltage=sensor_2_voltage,
            )

            # New side panels explicitly call it live_time_s.
            self.control_live_panel.add_plot_sample(
                live_time_s=live_time_s,
                sensor_1_voltage=sensor_1_voltage,
                sensor_2_voltage=sensor_2_voltage,
            )

            self.sequence_live_panel.add_plot_sample(
                live_time_s=live_time_s,
                sensor_1_voltage=sensor_1_voltage,
                sensor_2_voltage=sensor_2_voltage,
            )

        except Exception as exc:

            self._handle_runtime_error(
                exc
            )

    # =================================================================
    # MAIN FAN
    # =================================================================

    def _set_main_fan_active(
        self,
        active: bool,
    ) -> None:
        """Handle manual Main Fan ON/OFF."""

        if self.sequence.is_running():
            return

        try:

            if active:
                self.main_fan.on()
            else:
                self.main_fan.off()

            state = (
                self.main_fan.get_state()
            )

            self.session.set_main_fan_state(
                active=state.active,
                pwm_percent=state.pwm_percent,
            )

            self._log_state_change_events()
            self._update_gui()

        except Exception as exc:

            self._handle_runtime_error(
                exc
            )

    def _set_main_fan_pwm(
        self,
        pwm_percent: int,
    ) -> None:
        """Handle manual Main Fan PWM."""

        if self.sequence.is_running():
            return

        try:

            self.main_fan.set_pwm(
                pwm_percent
            )

            state = (
                self.main_fan.get_state()
            )

            self.session.set_main_fan_state(
                active=state.active,
                pwm_percent=state.pwm_percent,
            )

            self._log_state_change_events()
            self._update_gui()

        except Exception as exc:

            self._handle_runtime_error(
                exc
            )

    # =================================================================
    # SMOKE FAN
    # =================================================================

    def _set_smoke_fan_active(
        self,
        active: bool,
    ) -> None:
        """Handle manual Smoke Fan ON/OFF."""

        if self.sequence.is_running():
            return

        try:

            if active:
                self.smoke_fan.on()
            else:
                self.smoke_fan.off()

            state = (
                self.smoke_fan.get_state()
            )

            self.session.set_smoke_fan_state(
                active=state.active,
                pwm_percent=state.pwm_percent,
            )

            self._log_state_change_events()
            self._update_gui()

        except Exception as exc:

            self._handle_runtime_error(
                exc
            )

    def _set_smoke_fan_pwm(
        self,
        pwm_percent: int,
    ) -> None:
        """Handle manual Smoke Fan PWM."""

        if self.sequence.is_running():
            return

        try:

            self.smoke_fan.set_pwm(
                pwm_percent
            )

            state = (
                self.smoke_fan.get_state()
            )

            self.session.set_smoke_fan_state(
                active=state.active,
                pwm_percent=state.pwm_percent,
            )

            self._log_state_change_events()
            self._update_gui()

        except Exception as exc:

            self._handle_runtime_error(
                exc
            )

    # =================================================================
    # SENSOR 1
    # =================================================================

    def _set_sensor_1_active(
        self,
        active: bool,
    ) -> None:
        """Enable/disable Sensor 1 and its LED."""

        if self.sequence.is_running():
            return

        try:

            self.sensor_1.set_active(
                active
            )

            self.session.set_sensor_1_active(
                active
            )

            self._log_state_change_events()
            self._update_gui()

        except Exception as exc:

            self._handle_runtime_error(
                exc
            )

    # =================================================================
    # SENSOR 2
    # =================================================================

    def _set_sensor_2_active(
        self,
        active: bool,
    ) -> None:
        """Enable/disable Sensor 2 and its LED."""

        if self.sequence.is_running():
            return

        try:

            self.sensor_2.set_active(
                active
            )

            self.session.set_sensor_2_active(
                active
            )

            self._log_state_change_events()
            self._update_gui()

        except Exception as exc:

            self._handle_runtime_error(
                exc
            )

    # =================================================================
    # SMOKE MACHINE
    # =================================================================

    def _set_smoke_machine_active(
        self,
        active: bool,
    ) -> None:
        """
        Update manual smoke-machine log state.

        This is intentionally allowed during a sequence.
        """

        self.session.set_smoke_machine_active(
            active
        )

        self._log_state_change_events()
        self._update_gui()

    # =================================================================
    # MANUAL RECORDING
    # =================================================================

    def _start_recording(self) -> None:
        """Start recording from CONTROL."""

        if self.sequence.is_running():
            return

        if self.logger.is_recording():
            return

        metadata = (
            self.control_tab.get_test_metadata()
        )

        self.session.set_metadata(
            test_name=metadata["test_name"],
            mount_name=metadata["mount_name"],
            comment=metadata["comment"],
        )

        try:

            self.logger.start()

            # This recording belongs to CONTROL/manual workflow.
            self._recording_started_by_sequence = False

            # Synchronize event baseline AFTER recording starts.
            #
            # This prevents old state changes from before the recording
            # being written as new events.
            self._last_event_state = (
                self._get_event_state_snapshot()
            )

            self._clear_all_plots()

            self.control_tab.set_recording_state(
                True
            )

            self._update_gui()

        except Exception as exc:

            self._recording_started_by_sequence = False

            self._show_error(
                "Could not start recording",
                exc,
            )

    def _stop_recording(self) -> None:
        """Stop manual recording."""

        if self.sequence.is_running():
            return

        if not self.logger.is_recording():
            return

        try:

            # A manual Stop Recording button should only normally be
            # available for a manual recording.
            #
            # Guard against accidentally stopping sequence-owned data.
            if self._recording_started_by_sequence:
                return

            self.logger.log_event(
                "recording_stopped",
                "manual",
            )

            self.logger.stop()

            self._recording_started_by_sequence = False

            self.control_tab.set_recording_state(
                False
            )

            self._update_gui()

        except Exception as exc:

            self._show_error(
                "Could not stop recording",
                exc,
            )

    # =================================================================
    # START SEQUENCE
    # =================================================================

    def _start_sequence(
        self,
        step_data: list,
    ) -> None:
        """
        Start automatic sequence.

        Workflow:

            1. Read sequence options
            2. Reject recorded sequence if another recording is active
            3. Build/validate sequence steps
            4. Apply selected sensor states
            5. Start recording if requested
            6. Start sequence
            7. Lock manual controls

        An unrecorded sequence is allowed while a manual recording is
        already active. That manual recording remains manual-owned.
        """

        if self.sequence.is_running():
            return

        record_sequence = (
            self.sequence_tab.get_record_sequence()
        )

        # ------------------------------------------------------------
        # Recording conflict
        # ------------------------------------------------------------

        if (
            record_sequence
            and self.logger.is_recording()
        ):

            QMessageBox.warning(
                self,
                "Recording already active",
                (
                    "A recording is already active.\n\n"
                    "Stop the current manual recording before "
                    "starting a sequence with 'Record sequence' enabled."
                ),
            )

            return

        try:

            # --------------------------------------------------------
            # Convert GUI rows
            # --------------------------------------------------------

            steps = [
                SequenceStep(
                    duration_s=step[
                        "duration_s"
                    ],

                    main_fan_active=step[
                        "main_fan_active"
                    ],

                    main_fan_pwm_percent=step[
                        "main_fan_pwm_percent"
                    ],

                    smoke_fan_active=step[
                        "smoke_fan_active"
                    ],

                    smoke_fan_pwm_percent=step[
                        "smoke_fan_pwm_percent"
                    ],
                )
                for step in step_data
            ]

            if not steps:
                raise ValueError(
                    "The sequence contains no steps."
                )

            self.sequence.set_steps(
                steps
            )

            # --------------------------------------------------------
            # Sequence-selected sensors are authoritative at Run.
            # --------------------------------------------------------

            sensor_1_selected = (
                self.sequence_tab.get_sensor_1_selected()
            )

            sensor_2_selected = (
                self.sequence_tab.get_sensor_2_selected()
            )

            self.sensor_1.set_active(
                sensor_1_selected
            )

            self.session.set_sensor_1_active(
                sensor_1_selected
            )

            self.sensor_2.set_active(
                sensor_2_selected
            )

            self.session.set_sensor_2_active(
                sensor_2_selected
            )

            # Sensor changes happened before sequence-owned recording
            # by design. Update event baseline so they are not falsely
            # logged later.
            self._log_state_change_events()

            # --------------------------------------------------------
            # Automatic sequence recording
            # --------------------------------------------------------

            if record_sequence:

                metadata = (
                    self.sequence_tab.get_test_metadata()
                )

                self.session.set_metadata(
                    test_name=metadata["test_name"],
                    mount_name=metadata["mount_name"],
                    comment=metadata["comment"],
                )

                self.logger.start()

                self._recording_started_by_sequence = True

                self._last_event_state = (
                    self._get_event_state_snapshot()
                )

                self._clear_all_plots()

            # --------------------------------------------------------
            # Start sequence
            # --------------------------------------------------------

            self.sequence.start()

            # Sequence.start() applies Step 1 immediately.
            # Capture fan changes caused by Step 1.
            self._log_state_change_events()

            if self.logger.is_recording():

                self.logger.log_event(
                    "sequence_started",
                    {
                        "record_sequence":
                            record_sequence,

                        "step_count":
                            len(steps),

                        "total_duration_s":
                            sum(
                                step.duration_s
                                for step in steps
                            ),
                    },
                )

            # --------------------------------------------------------
            # Lock UI
            # --------------------------------------------------------

            self.control_tab.set_sequence_running(
                True
            )

            self.sequence_tab.set_sequence_running(
                True
            )

            self._update_gui()

        except Exception as exc:

            # --------------------------------------------------------
            # Roll back a sequence-owned recording if sequence startup
            # fails after logger.start().
            # --------------------------------------------------------

            if (
                self._recording_started_by_sequence
                and self.logger.is_recording()
            ):

                try:
                    self.logger.log_event(
                        "sequence_start_failed",
                        str(exc),
                    )

                    self.logger.stop()

                except Exception:
                    pass

            self._recording_started_by_sequence = False

            # Ensure sequence/fans are safe if startup partially failed.
            try:
                self.sequence.stop()
            except Exception:
                pass

            self.control_tab.set_sequence_running(
                False
            )

            self.sequence_tab.set_sequence_running(
                False
            )

            self._update_gui()

            self._show_error(
                "Could not start sequence",
                exc,
            )

    # =================================================================
    # MANUAL SEQUENCE STOP
    # =================================================================

    def _stop_sequence(self) -> None:
        """Stop sequence from the SEQUENCE tab."""

        if not self.sequence.is_running():
            return

        try:

            self.sequence.stop()

            # Capture automatic fan OFF / PWM 0 changes while the
            # sequence recording is still open.
            self._log_state_change_events()

            if self.logger.is_recording():

                self.logger.log_event(
                    "sequence_stopped",
                    "manual",
                )

            # --------------------------------------------------------
            # Stop recording only if the sequence owns it.
            # --------------------------------------------------------

            if (
                self._recording_started_by_sequence
                and self.logger.is_recording()
            ):

                self.logger.stop()

            self._recording_started_by_sequence = False

            self.control_tab.set_sequence_running(
                False
            )

            self.sequence_tab.set_sequence_running(
                False
            )

            self._update_gui()

        except Exception as exc:

            self._handle_runtime_error(
                exc
            )

    # =================================================================
    # NORMAL SEQUENCE COMPLETION
    # =================================================================

    def _handle_sequence_completed(
        self,
    ) -> None:
        """
        Handle transition from running sequence to normal completion.

        SequenceController has already:
            - stopped both fans
            - set PWM to zero
            - marked sequence_running False
        """

        # Capture fan stop caused by normal completion.
        self._log_state_change_events()

        if self.logger.is_recording():

            self.logger.log_event(
                "sequence_completed"
            )

        # ------------------------------------------------------------
        # Stop only sequence-owned recording.
        #
        # If an unrecorded sequence was running during a manual
        # recording, that manual recording must continue.
        # ------------------------------------------------------------

        if (
            self._recording_started_by_sequence
            and self.logger.is_recording()
        ):

            self.logger.stop()

        self._recording_started_by_sequence = False

        self.control_tab.set_sequence_running(
            False
        )

        self.sequence_tab.set_sequence_running(
            False
        )

        self._update_gui()

    # =================================================================
    # STOP ALL
    # =================================================================

    def _stop_all(self) -> None:
        """
        STOP ALL safety action.

        Always:
            - Stop Main Fan
            - Main PWM -> 0 %
            - Stop Smoke Fan
            - Smoke PWM -> 0 %
            - Stop running sequence

        Never:
            - Disable sensors
            - Change smoke-machine logged state

        Recording:
            - Manual recording continues
            - Sequence-owned recording stops
        """

        try:

            sequence_was_running = (
                self.sequence.is_running()
            )

            sequence_owned_recording = (
                self._recording_started_by_sequence
                and self.logger.is_recording()
            )

            # --------------------------------------------------------
            # Stop sequence / fans
            # --------------------------------------------------------

            if sequence_was_running:

                self.sequence.stop()

            else:

                self.main_fan.stop()
                self.smoke_fan.stop()

            self.session.apply_stop_all_state()

            # --------------------------------------------------------
            # Log resulting fan state changes
            # --------------------------------------------------------

            self._log_state_change_events()

            # --------------------------------------------------------
            # Explicit workflow events
            # --------------------------------------------------------

            if self.logger.is_recording():

                if sequence_was_running:

                    self.logger.log_event(
                        "sequence_stopped",
                        "stop_all",
                    )

                self.logger.log_event(
                    "stop_all"
                )

            # --------------------------------------------------------
            # Recording ownership
            # --------------------------------------------------------

            if sequence_owned_recording:

                self.logger.stop()

                self._recording_started_by_sequence = False

            # Manual recording intentionally continues.

            self.control_tab.set_sequence_running(
                False
            )

            self.sequence_tab.set_sequence_running(
                False
            )

            self._update_gui()

        except Exception as exc:

            self._handle_runtime_error(
                exc
            )

    # =================================================================
    # EVENT STATE
    # =================================================================

    def _get_event_state_snapshot(
        self,
    ) -> dict:
        """Return all discrete states that should generate events."""

        return {
            "main_fan_active":
                bool(
                    self.session.main_fan_active
                ),

            "main_fan_pwm_percent":
                int(
                    self.session.main_fan_pwm_percent
                ),

            "smoke_fan_active":
                bool(
                    self.session.smoke_fan_active
                ),

            "smoke_fan_pwm_percent":
                int(
                    self.session.smoke_fan_pwm_percent
                ),

            "smoke_machine_active":
                bool(
                    self.session.smoke_machine_active
                ),

            "sensor_1_active":
                bool(
                    self.session.sensor_1_active
                ),

            "sensor_2_active":
                bool(
                    self.session.sensor_2_active
                ),
        }

    def _log_state_change_events(self) -> None:
        """
        Detect discrete state changes and write event records.

        The snapshot is updated even when not recording.

        This prevents changes made before a recording from being
        incorrectly logged after recording starts.
        """

        current = (
            self._get_event_state_snapshot()
        )

        previous = (
            self._last_event_state
        )

        if self.logger.is_recording():

            # --------------------------------------------------------
            # Main fan active
            # --------------------------------------------------------

            if (
                current["main_fan_active"]
                != previous["main_fan_active"]
            ):

                self.logger.log_event(
                    (
                        "main_fan_on"
                        if current["main_fan_active"]
                        else "main_fan_off"
                    )
                )

            # --------------------------------------------------------
            # Main fan PWM
            # --------------------------------------------------------

            if (
                current["main_fan_pwm_percent"]
                != previous["main_fan_pwm_percent"]
            ):

                self.logger.log_event(
                    "main_fan_pwm_changed",
                    {
                        "pwm_percent":
                            current[
                                "main_fan_pwm_percent"
                            ]
                    },
                )

            # --------------------------------------------------------
            # Smoke fan active
            # --------------------------------------------------------

            if (
                current["smoke_fan_active"]
                != previous["smoke_fan_active"]
            ):

                self.logger.log_event(
                    (
                        "smoke_fan_on"
                        if current["smoke_fan_active"]
                        else "smoke_fan_off"
                    )
                )

            # --------------------------------------------------------
            # Smoke fan PWM
            # --------------------------------------------------------

            if (
                current["smoke_fan_pwm_percent"]
                != previous["smoke_fan_pwm_percent"]
            ):

                self.logger.log_event(
                    "smoke_fan_pwm_changed",
                    {
                        "pwm_percent":
                            current[
                                "smoke_fan_pwm_percent"
                            ]
                    },
                )

            # --------------------------------------------------------
            # Smoke machine
            # --------------------------------------------------------

            if (
                current["smoke_machine_active"]
                != previous["smoke_machine_active"]
            ):

                self.logger.log_event(
                    (
                        "smoke_machine_on"
                        if current[
                            "smoke_machine_active"
                        ]
                        else "smoke_machine_off"
                    )
                )

            # --------------------------------------------------------
            # Sensor 1
            # --------------------------------------------------------

            if (
                current["sensor_1_active"]
                != previous["sensor_1_active"]
            ):

                self.logger.log_event(
                    (
                        "sensor_1_on"
                        if current["sensor_1_active"]
                        else "sensor_1_off"
                    )
                )

            # --------------------------------------------------------
            # Sensor 2
            # --------------------------------------------------------

            if (
                current["sensor_2_active"]
                != previous["sensor_2_active"]
            ):

                self.logger.log_event(
                    (
                        "sensor_2_on"
                        if current["sensor_2_active"]
                        else "sensor_2_off"
                    )
                )

        self._last_event_state = current

    # =================================================================
    # PLOT HELPERS
    # =================================================================

    def _clear_all_plots(self) -> None:
        """Clear all three live plot displays."""

        self.live_tab.clear_plots()
        self.control_live_panel.clear_plots()
        self.sequence_live_panel.clear_plots()

    # =================================================================
    # GUI SYNCHRONIZATION
    # =================================================================

    def _update_gui(self) -> None:
        """Synchronize all GUI displays with TestSession."""

        sequence_running = (
            self.sequence.is_running()
        )

        # ------------------------------------------------------------
        # CONTROL
        # ------------------------------------------------------------

        self.control_tab.set_main_fan_active(
            self.session.main_fan_active
        )

        self.control_tab.set_main_fan_pwm(
            self.session.main_fan_pwm_percent
        )

        self.control_tab.set_smoke_fan_active(
            self.session.smoke_fan_active
        )

        self.control_tab.set_smoke_fan_pwm(
            self.session.smoke_fan_pwm_percent
        )

        self.control_tab.set_sensor_1_active(
            self.session.sensor_1_active
        )

        self.control_tab.set_sensor_2_active(
            self.session.sensor_2_active
        )

        self.control_tab.set_smoke_machine_active(
            self.session.smoke_machine_active
        )

        self.control_tab.set_recording_state(
            self.logger.is_recording()
        )

        self.control_tab.set_sequence_running(
            sequence_running
        )

        # ------------------------------------------------------------
        # SEQUENCE
        # ------------------------------------------------------------

        self.sequence_tab.set_sequence_running(
            sequence_running
        )

        # Smoke-machine controls in CONTROL and SEQUENCE always
        # represent the same TestSession state.
        self.sequence_tab.set_smoke_machine_active(
            self.session.smoke_machine_active
        )

        # ------------------------------------------------------------
        # Shared live display values
        # ------------------------------------------------------------

        sensor_kwargs = {
            "sensor_1_active":
                self.session.sensor_1_active,

            "sensor_1_voltage":
                self.session.sensor_1_voltage_v,

            "sensor_2_active":
                self.session.sensor_2_active,

            "sensor_2_voltage":
                self.session.sensor_2_voltage_v,
        }

        fan_kwargs = {
            "main_fan_active":
                self.session.main_fan_active,

            "main_fan_pwm_percent":
                self.session.main_fan_pwm_percent,

            "smoke_fan_active":
                self.session.smoke_fan_active,

            "smoke_fan_pwm_percent":
                self.session.smoke_fan_pwm_percent,
        }

        experiment_kwargs = {
            "recording":
                self.logger.is_recording(),

            "elapsed_time_s":
                self.session.get_elapsed_time_s(),

            "smoke_machine_active":
                self.session.smoke_machine_active,

            "sequence_running":
                sequence_running,

            "sequence_step":
                self.sequence.get_current_step_number(),
        }

        for display in (
            self.live_tab,
            self.control_live_panel,
            self.sequence_live_panel,
        ):

            display.update_sensor_values(
                **sensor_kwargs
            )

            display.update_fan_status(
                **fan_kwargs
            )

            display.update_experiment_status(
                **experiment_kwargs
            )

    # =================================================================
    # ERROR HANDLING
    # =================================================================

    def _handle_runtime_error(
        self,
        exception: Exception,
    ) -> None:
        """
        Handle serious runtime error.

        The update timer is stopped and fan outputs are placed in a
        safe state.
        """

        if hasattr(
            self,
            "update_timer",
        ):

            self.update_timer.stop()

        # ------------------------------------------------------------
        # Stop sequence / fans
        # ------------------------------------------------------------

        try:

            if self.sequence.is_running():
                self.sequence.stop()

        except Exception:
            pass

        try:
            self.main_fan.stop()
        except Exception:
            pass

        try:
            self.smoke_fan.stop()
        except Exception:
            pass

        self.session.apply_stop_all_state()

        # ------------------------------------------------------------
        # Preserve recording file if possible
        # ------------------------------------------------------------

        try:

            if self.logger.is_recording():

                self.logger.log_event(
                    "runtime_error",
                    str(exception),
                )

                self.logger.stop()

        except Exception:
            pass

        self._recording_started_by_sequence = False

        try:
            self._update_gui()
        except Exception:
            pass

        self._show_error(
            "Runtime error",
            exception,
        )

    @staticmethod
    def _show_error(
        title: str,
        exception: Exception,
    ) -> None:
        """Display error dialog."""

        QMessageBox.critical(
            None,
            title,
            str(exception),
        )

    # =================================================================
    # CLEANUP
    # =================================================================

    def cleanup(self) -> None:
        """Safely shut down complete application."""

        if self._cleanup_done:
            return

        self._cleanup_done = True

        # ------------------------------------------------------------
        # Timer
        # ------------------------------------------------------------

        if hasattr(
            self,
            "update_timer",
        ):

            self.update_timer.stop()

        # ------------------------------------------------------------
        # Logger
        # ------------------------------------------------------------

        try:

            if self.logger.is_recording():

                self.logger.log_event(
                    "application_closed"
                )

            self.logger.cleanup()

        except Exception:
            pass

        # ------------------------------------------------------------
        # Sequence
        # ------------------------------------------------------------

        try:
            self.sequence.cleanup()
        except Exception:
            pass

        # ------------------------------------------------------------
        # Sensors
        # ------------------------------------------------------------

        try:
            self.sensor_1.cleanup()
        except Exception:
            pass

        try:
            self.sensor_2.cleanup()
        except Exception:
            pass

        # ------------------------------------------------------------
        # Fans
        # ------------------------------------------------------------

        try:
            self.main_fan.cleanup()
        except Exception:
            pass

        try:
            self.smoke_fan.cleanup()
        except Exception:
            pass

        # ------------------------------------------------------------
        # LEDs
        # ------------------------------------------------------------

        try:
            self.sensor_1_led.cleanup()
        except Exception:
            pass

        try:
            self.sensor_2_led.cleanup()
        except Exception:
            pass

        # ------------------------------------------------------------
        # ADC
        # ------------------------------------------------------------

        try:
            self.adc.close()
        except Exception:
            pass

    def closeEvent(
        self,
        event,
    ) -> None:
        """Qt window-close event."""

        self.cleanup()

        event.accept()