"""
gui/main_window.py

Main application window for the airflow/smoke test bench.

MainWindow coordinates:

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

MainWindow owns:
    - Manual recording
    - Sequence-owned recording
    - Recording ownership
    - Sequence completion handling
    - Event logging
    - STOP ALL behavior
    - Sensor selection for sequences
    - Smoke-machine state synchronization
    - Independent live-plot timebase
    - Live plot freeze/resume control
    - Optional freeze when a sequence ends
    - Sequence-step graph markers
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QMessageBox,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QLabel,
    QFrame,
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

from gui.styles import (
    APP_STYLESHEET,
    CARD_SPACING,
)


# =====================================================================
# HARDWARE BACKEND
# =====================================================================


def _load_hardware_backend():
    """
    Import real or simulated hardware backend.

    Raspberry Pi libraries are only imported in real mode.
    This allows the complete GUI to run on Windows.
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


# =====================================================================
# MAIN WINDOW
# =====================================================================


class MainWindow(QMainWindow):
    """Main test-bench application window."""

    # =================================================================
    # INITIALIZATION
    # =================================================================

    def __init__(self) -> None:
        """Initialize complete application."""

        super().__init__()

        # -------------------------------------------------------------
        # Window
        # -------------------------------------------------------------

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
            1400,
            900,
        )

        self.setStyleSheet(
            APP_STYLESHEET
        )

        self._cleanup_done = False

        # -------------------------------------------------------------
        # Independent live graph timebase
        #
        # This is NOT recording elapsed time.
        # -------------------------------------------------------------

        self._live_start_monotonic = (
            time.monotonic()
        )

        # Used for sequence-step graph markers.
        self._last_sequence_step = None

        # -------------------------------------------------------------
        # Live plot state
        #
        # Plotting is deliberately separate from sensor acquisition
        # and CSV recording. Turning the live plot OFF only freezes the
        # graphs; sensor values and logging continue normally.
        # -------------------------------------------------------------

        self._live_plot_enabled = True

        # Pause-aware graph clock.
        #
        # When plotting is frozen, graph time also pauses. When plotting
        # resumes, the X-axis continues from where it stopped instead of
        # jumping forward by the frozen duration.
        self._live_plot_paused_at_monotonic = None
        self._live_plot_paused_total_s = 0.0

        # Sequence option captured when RUN SEQUENCE is pressed.
        self._freeze_plot_after_sequence = False

        # -------------------------------------------------------------
        # Recording ownership
        #
        # False:
        #     no recording, or recording started manually.
        #
        # True:
        #     recording automatically started by sequence.
        # -------------------------------------------------------------

        self._recording_started_by_sequence = False

        # -------------------------------------------------------------
        # Camera state
        # -------------------------------------------------------------

        self.camera = None
        self._camera_enabled = False
        self._camera_record_video = False
        self._camera_preview_frame = None
        self._camera_recording_active = False
        self._camera_error_logged = False

        # -------------------------------------------------------------
        # Application state
        # -------------------------------------------------------------

        self.session = TestSession()

        # -------------------------------------------------------------
        # Hardware / simulation
        # -------------------------------------------------------------

        self._initialize_hardware()

        # -------------------------------------------------------------
        # Services
        # -------------------------------------------------------------

        self.logger = DataLogger(
            session=self.session
        )

        self.sequence = SequenceController(
            main_fan=self.main_fan,
            smoke_fan=self.smoke_fan,
            session=self.session,
        )

        # -------------------------------------------------------------
        # Event-state snapshot
        # -------------------------------------------------------------

        self._last_event_state = (
            self._get_event_state_snapshot()
        )

        # -------------------------------------------------------------
        # GUI
        # -------------------------------------------------------------

        self._build_ui()

        self._initialize_camera()

        self._connect_signals()

        # -------------------------------------------------------------
        # Main update timer
        # -------------------------------------------------------------

        self._create_update_timer()

        # -------------------------------------------------------------
        # Initial display synchronization
        # -------------------------------------------------------------

        self._update_gui()

    # =================================================================
    # HARDWARE INITIALIZATION
    # =================================================================

    def _initialize_hardware(
        self,
    ) -> None:
        """
        Initialize real or simulated hardware.

        Real mode:
            - Two fan controllers
            - Two FG/RPM monitors
            - ADS1115
            - Two logical LED interfaces
            - Two optical sensors

        Simulation mode:
            - Existing simulation backends
            - No physical FG monitoring
        """

        (
            FanController,
            ADCController,
            LEDController,
            OpticalSensor,
        ) = _load_hardware_backend()

        # --------------------------------------------------------
        # FAN CONTROLLERS
        # --------------------------------------------------------

        self.main_fan = FanController(
            gpio_pin=config.MAIN_FAN_PWM_GPIO,
            name="Main Fan",
        )

        self.smoke_fan = FanController(
            gpio_pin=config.SMOKE_FAN_PWM_GPIO,
            name="Smoke Fan",
        )

        # --------------------------------------------------------
        # RPM MONITORS
        # --------------------------------------------------------

        self.main_fan_rpm_monitor = None
        self.smoke_fan_rpm_monitor = None

        if config.HARDWARE_MODE == "real":

            from hardware.fan_rpm import FanRPMMonitor

            self.main_fan_rpm_monitor = FanRPMMonitor(
                gpio_pin=config.MAIN_FAN_FG_GPIO,
                name="Main Fan",
                pulses_per_revolution=2,
            )

            self.smoke_fan_rpm_monitor = FanRPMMonitor(
                gpio_pin=config.SMOKE_FAN_FG_GPIO,
                name="Smoke Fan",
                pulses_per_revolution=2,
            )

        # --------------------------------------------------------
        # ADC
        # --------------------------------------------------------

        self.adc = ADCController()

        # --------------------------------------------------------
        # LED INTERFACES
        # --------------------------------------------------------

        self.sensor_1_led = LEDController(
            gpio_pin=config.SENSOR_1_LED_GPIO,
            name="Sensor 1 LED",
        )

        self.sensor_2_led = LEDController(
            gpio_pin=config.SENSOR_2_LED_GPIO,
            name="Sensor 2 LED",
        )

        # --------------------------------------------------------
        # OPTICAL SENSORS
        # --------------------------------------------------------

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

    def _initialize_camera(
        self,
    ) -> None:
        """Create the independent OpenCV USB camera backend."""

        try:
            from hardware.camera import CameraController
        except Exception:
            from simulation.camera import CameraController

        self.camera = CameraController(
            camera_index=0,
            preview_size=config.DEFAULT_CAMERA_PREVIEW_SIZE,
            target_fps=config.DEFAULT_CAMERA_TARGET_FPS,
        )
        self.camera.set_video_frame_callback(
            self.logger.log_video_frame_timestamp
        )

        self.camera_2 = CameraController(
            camera_index=1,
            preview_size=config.DEFAULT_CAMERA_PREVIEW_SIZE,
            target_fps=config.DEFAULT_CAMERA_TARGET_FPS,
        )

        self.control_tab.set_camera_source_options(
            self.camera.available_devices()
        )

        self._camera_enabled = False
        self._camera_record_video = False
        self._camera_recording_active = False
        self._camera_preview_frame = None
        self._camera_error_logged = False

        self._camera_2_enabled = False
        self._camera_2_record_video = False

        self._update_camera_dropdowns()

        self.logger.set_camera_available(
            self.camera.is_available()
        )
        self.control_tab.set_auto_exposure_enabled(
            self.camera.get_auto_exposure() if self.camera.supports_auto_exposure() else False,
            supported=self.camera.supports_auto_exposure(),
        )
        self.control_tab.set_exposure_value(
            self.camera.get_exposure() if self.camera.supports_exposure() else None,
            supported=self.camera.supports_exposure(),
        )
        self.control_tab.set_gain_value(
            self.camera.get_gain() if self.camera.supports_gain() else None,
            supported=self.camera.supports_gain(),
        )

    def _update_camera_dropdowns(self) -> None:
        """Synchronize the camera source dropdowns with the currently available devices."""

        devices = self.camera.available_devices() if self.camera is not None else []

        self.control_tab.camera_source_combo.blockSignals(True)
        self.control_tab.camera_source_combo.clear()
        for index, label in devices:
            self.control_tab.camera_source_combo.addItem(label, index)
        self.control_tab.camera_source_combo.setEnabled(bool(devices) and not self._camera_enabled)
        self.control_tab.camera_source_combo.blockSignals(False)

        excluded_index = None
        if self.camera is not None and self._camera_enabled:
            excluded_index = self.camera.camera_index

        secondary_devices = devices
        if excluded_index is not None:
            secondary_devices = [
                (index, label) for index, label in devices if index != excluded_index
            ]

        self.control_tab.camera_2_source_combo.blockSignals(True)
        self.control_tab.camera_2_source_combo.clear()
        for index, label in secondary_devices:
            self.control_tab.camera_2_source_combo.addItem(label, index)
        self.control_tab.camera_2_source_combo.setEnabled(bool(secondary_devices))
        self.control_tab.camera_2_source_combo.blockSignals(False)

    def _build_ui(
        self,
    ) -> None:
        """Build main three-tab interface."""

        self.tabs = QTabWidget()

        # -------------------------------------------------------------
        # Main tab widgets
        # -------------------------------------------------------------

        self.control_tab = ControlTab()

        self.live_tab = LiveTab()

        self.sequence_tab = SequenceTab()

        # -------------------------------------------------------------
        # Compact right-side panels
        # -------------------------------------------------------------

        self.control_live_panel = LiveStatusPanel()

        self.sequence_live_panel = LiveStatusPanel()

        # -------------------------------------------------------------
        # CONTROL
        # -------------------------------------------------------------

        control_page = (
            self._wrap_with_live_panel(
                left_widget=self.control_tab,
                live_panel=self.control_live_panel,
                bottom_widget=self.control_tab.stop_all_button,
            )
        )

        self.tabs.addTab(
            control_page,
            "CONTROL",
        )

        # -------------------------------------------------------------
        # LIVE DATA
        # -------------------------------------------------------------

        self.tabs.addTab(
            self.live_tab,
            "LIVE DATA",
        )

        # -------------------------------------------------------------
        # SEQUENCE
        # -------------------------------------------------------------

        sequence_page = (
            self._wrap_with_live_panel(
                left_widget=self.sequence_tab,
                live_panel=self.sequence_live_panel,
            )
        )

        self.tabs.addTab(
            sequence_page,
            "SEQUENCE",
        )

        central_widget = QWidget()
        central_layout = QVBoxLayout(
            central_widget
        )
        central_layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )
        central_layout.setSpacing(
            10,
        )
        central_layout.addWidget(
            self._build_brand_header(),
            stretch=0,
        )
        central_layout.addWidget(
            self.tabs,
            stretch=1,
        )

        self.setCentralWidget(
            central_widget
        )

    @staticmethod
    def _build_brand_header() -> QWidget:
        """Create a shared brand header for all tabs/pages."""

        header = QFrame()
        header.setProperty(
            "card",
            True,
        )
        header.setFixedHeight(
            80
        )

        logo_layout = QHBoxLayout(
            header
        )
        logo_layout.setContentsMargins(
            18,
            10,
            18,
            10,
        )
        logo_layout.setSpacing(
            18,
        )

        pictures_dir = (
            Path(__file__).resolve().parents[1]
            / "pictures"
        )
        logo_files = [
            "aarhus_university_logo.svg",
            "Gemini_Generated_Image_u4ow2uu4ow2uu4ow (1).jpg",
            "kisspng-logo-brand-product-design-font-file-agco-logo-svg-wikipedia-5b6e40587d57f6.8986170015339520885134.jpg",
        ]

        def _make_logo_label(path: Path) -> QLabel:
            label = QLabel()
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                label.setPixmap(
                    pixmap.scaled(
                        140,
                        42,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                label.setText(path.stem)
            label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            return label

        left_logo_group = QHBoxLayout()
        left_logo_group.setSpacing(12)
        for file_name in logo_files[:1]:
            left_logo_group.addWidget(
                _make_logo_label(
                    pictures_dir / file_name
                )
            )

        right_logo_group = QHBoxLayout()
        right_logo_group.setSpacing(12)
        for file_name in logo_files[1:]:
            right_logo_group.addWidget(
                _make_logo_label(
                    pictures_dir / file_name
                )
            )

        title_label = QLabel(
            config.APP_NAME.upper()
        )
        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        title_label.setStyleSheet(
            "QLabel { font-size: 18px; font-weight: 700; letter-spacing: 1.2px; }"
        )

        logo_layout.addLayout(
            left_logo_group
        )
        logo_layout.addStretch()
        logo_layout.addWidget(
            title_label,
            stretch=1,
        )
        logo_layout.addStretch()
        logo_layout.addLayout(
            right_logo_group
        )

        return header

    # =================================================================
    # TAB WRAPPER
    # =================================================================

    @staticmethod
    def _wrap_with_live_panel(
        left_widget: QWidget,
        live_panel: LiveStatusPanel,
        bottom_widget: QWidget | None = None,
    ) -> QWidget:
        """
        Place main tab content beside compact live panel.

        CONTROL supplies STOP ALL as bottom_widget.

        That moves the existing ControlTab STOP ALL button visually
        below the Live Status / Live Data column without changing
        its signal or functionality.
        """

        container = QWidget()

        outer_layout = QHBoxLayout(
            container
        )

        outer_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        outer_layout.setSpacing(
            0
        )

        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        # -------------------------------------------------------------
        # Left side
        # -------------------------------------------------------------

        splitter.addWidget(
            left_widget
        )

        # -------------------------------------------------------------
        # Right side
        # -------------------------------------------------------------

        right_container = QWidget()

        right_layout = QVBoxLayout(
            right_container
        )

        right_layout.setContentsMargins(
            CARD_SPACING,
            CARD_SPACING,
            CARD_SPACING,
            CARD_SPACING,
        )

        right_layout.setSpacing(
            CARD_SPACING
        )

        right_layout.addWidget(
            live_panel,
            stretch=1,
        )

        # -------------------------------------------------------------
        # Optional bottom control
        #
        # Used for CONTROL's STOP ALL button.
        # -------------------------------------------------------------

        if bottom_widget is not None:

            left_layout = (
                left_widget.layout()
            )

            if left_layout is not None:

                left_layout.removeWidget(
                    bottom_widget
                )

            right_layout.addWidget(
                bottom_widget
            )

        splitter.addWidget(
            right_container
        )

        # -------------------------------------------------------------
        # Relative size
        # -------------------------------------------------------------

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

        outer_layout.addWidget(
            splitter
        )

        return container

    # =================================================================
    # SIGNALS
    # =================================================================

    def _connect_signals(
        self,
    ) -> None:
        """Connect GUI signals to MainWindow handlers."""

        # -------------------------------------------------------------
        # Main fan
        # -------------------------------------------------------------

        self.control_tab.main_fan_active_changed.connect(
            self._set_main_fan_active
        )

        self.control_tab.main_fan_pwm_changed.connect(
            self._set_main_fan_pwm
        )

        # -------------------------------------------------------------
        # Smoke fan
        # -------------------------------------------------------------

        self.control_tab.smoke_fan_active_changed.connect(
            self._set_smoke_fan_active
        )

        self.control_tab.smoke_fan_pwm_changed.connect(
            self._set_smoke_fan_pwm
        )

        # -------------------------------------------------------------
        # Sensors
        # -------------------------------------------------------------

        self.control_tab.sensor_1_active_changed.connect(
            self._set_sensor_1_active
        )

        self.control_tab.sensor_2_active_changed.connect(
            self._set_sensor_2_active
        )

        # -------------------------------------------------------------
        # Smoke machine
        #
        # CONTROL and SEQUENCE represent same logical state.
        # -------------------------------------------------------------

        self.control_tab.smoke_machine_active_changed.connect(
            self._set_smoke_machine_active
        )

        self.sequence_tab.smoke_machine_active_changed.connect(
            self._set_smoke_machine_active
        )

        # -------------------------------------------------------------
        # Manual recording
        # -------------------------------------------------------------

        self.control_tab.start_recording_requested.connect(
            self._start_recording
        )

        self.control_tab.stop_recording_requested.connect(
            self._stop_recording
        )

        self.control_tab.camera_enabled_changed.connect(
            self._set_camera_enabled
        )

        self.control_tab.camera_2_enabled_changed.connect(
            self._set_camera_2_enabled
        )

        self.control_tab.camera_source_changed.connect(
            self._set_camera_source
        )

        self.control_tab.camera_2_source_changed.connect(
            self._set_camera_2_source
        )

        self.control_tab.auto_exposure_changed.connect(
            self._set_camera_auto_exposure
        )

        self.control_tab.camera_2_auto_exposure_changed.connect(
            self._set_camera_2_auto_exposure
        )

        self.control_tab.exposure_changed.connect(
            self._set_camera_exposure
        )

        self.control_tab.camera_2_exposure_changed.connect(
            self._set_camera_2_exposure
        )

        self.control_tab.gain_changed.connect(
            self._set_camera_gain
        )

        self.control_tab.camera_2_gain_changed.connect(
            self._set_camera_2_gain
        )

        self.control_tab.record_video_changed.connect(
            self._set_record_video
        )

        self.control_tab.camera_2_record_video_changed.connect(
            self._set_camera_2_record_video
        )

        # -------------------------------------------------------------
        # Live plot
        # -------------------------------------------------------------

        self.control_tab.live_plot_enabled_changed.connect(
            self._set_live_plot_enabled
        )

        # -------------------------------------------------------------
        # STOP ALL
        # -------------------------------------------------------------

        self.control_tab.stop_all_requested.connect(
            self._stop_all
        )

        # -------------------------------------------------------------
        # Sequence
        # -------------------------------------------------------------

        self.sequence_tab.run_sequence_requested.connect(
            self._start_sequence
        )

        self.sequence_tab.stop_sequence_requested.connect(
            self._stop_sequence
        )

    # =================================================================
    # TIMER
    # =================================================================

    def _create_update_timer(
        self,
    ) -> None:
        """Create the sensor loop and an independent camera preview timer."""

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

        self.camera_timer = QTimer(self)
        self.camera_timer.setInterval(33)
        self.camera_timer.timeout.connect(self._update_camera_state)
        self.camera_timer.start()

    # =================================================================
    # CENTRAL UPDATE LOOP
    # =================================================================

    def _update_loop(
        self,
    ) -> None:
        """
        Central periodic update.

        Order:

            1. Update sequence
            2. Detect sequence-step change
            3. Log sequence-driven state changes
            4. Detect sequence completion
            5. Read sensors exactly once
            6. Store sensor values
            7. Log one time-series sample if recording
            8. Update GUI
            9. Update graphs only if live plotting is enabled
        """

        try:

            # ---------------------------------------------------------
            # Sequence update
            # ---------------------------------------------------------

            sequence_was_running = (
                self.sequence.is_running()
            )

            self.sequence.update()

            sequence_is_running = (
                self.sequence.is_running()
            )

            # ---------------------------------------------------------
            # Detect sequence step transitions
            # ---------------------------------------------------------

            if sequence_is_running:

                current_step = (
                    self.sequence.get_current_step_number()
                )

                if (
                    self._live_plot_enabled
                    and current_step is not None
                    and current_step
                    != self._last_sequence_step
                ):

                    marker_time_s = (
                        self._get_live_plot_time_s()
                    )

                    self.live_tab.add_sequence_step_marker(
                        live_time_s=marker_time_s,
                        step_number=current_step,
                    )

                    self._last_sequence_step = (
                        current_step
                    )

            # ---------------------------------------------------------
            # Sequence can directly change fan state.
            # ---------------------------------------------------------

            self._log_state_change_events()

            # ---------------------------------------------------------
            # Normal sequence completion
            # ---------------------------------------------------------

            if (
                sequence_was_running
                and not sequence_is_running
            ):

                self._handle_sequence_completed()

            # ---------------------------------------------------------
            # Read both sensors exactly once
            # ---------------------------------------------------------

            sensor_1_voltage = (
                self.sensor_1.read_voltage()
            )

            sensor_2_voltage = (
                self.sensor_2.read_voltage()
            )

            # ---------------------------------------------------------
            # Camera preview / recording loop is handled by a dedicated
            # camera timer so the UI can refresh at ~30 FPS independent of the
            # 10 Hz sensor loop.
            # ---------------------------------------------------------

            elapsed_time_s = self.session.get_elapsed_time_s()
            step_number = self.sequence.get_current_step_number()
            step_label = "MANUAL" if step_number is None else f"STEP {int(step_number)}"
            sensor_1_label = "--V" if sensor_1_voltage is None else f"{float(sensor_1_voltage):.2f}V"
            sensor_2_label = "--V" if sensor_2_voltage is None else f"{float(sensor_2_voltage):.2f}V"
            overlay_string = (
                f"TIME: {float(elapsed_time_s):.1f}s | {step_label} | "
                f"S1: {sensor_1_label} | S2: {sensor_2_label}"
            )
            if self.camera is not None:
                self.camera.set_overlay_text(overlay_string)
            if self.camera_2 is not None:
                self.camera_2.set_overlay_text(overlay_string)

            # ---------------------------------------------------------
            # Store latest sensor measurements
            # ---------------------------------------------------------

            self.session.set_sensor_1_voltage(
                sensor_1_voltage
            )

            self.session.set_sensor_2_voltage(
                sensor_2_voltage
            )

            # ---------------------------------------------------------
            # Read measured fan RPM before CSV logging and GUI refresh.
            # Simulation has no physical FG signal: keep values unknown.
            # ---------------------------------------------------------

            main_rpm = (
                self.main_fan_rpm_monitor.get_rpm()
                if self.main_fan_rpm_monitor is not None
                else None
            )
            smoke_rpm = (
                self.smoke_fan_rpm_monitor.get_rpm()
                if self.smoke_fan_rpm_monitor is not None
                else None
            )

            self.session.set_main_fan_rpm(main_rpm)
            self.session.set_smoke_fan_rpm(smoke_rpm)

            # ---------------------------------------------------------
            # Time-series recording
            # ---------------------------------------------------------

            if self.logger.is_recording():

                self.logger.log_sample()

            # ---------------------------------------------------------
            # Update labels/status
            # ---------------------------------------------------------

            self._update_gui()

            # ---------------------------------------------------------
            # Independent GUI graph time / plotting
            #
            # Sensor acquisition, live numerical values and CSV logging
            # continue regardless of this state.
            # ---------------------------------------------------------

            if self._live_plot_enabled:

                live_time_s = (
                    self._get_live_plot_time_s()
                )

                # Main LIVE DATA graph
                self.live_tab.add_plot_sample(
                    live_time_s=live_time_s,
                    sensor_1_voltage=sensor_1_voltage,
                    sensor_2_voltage=sensor_2_voltage,
                    main_fan_rpm=self.session.main_fan_rpm,
                    smoke_fan_rpm=self.session.smoke_fan_rpm,
                )

                # CONTROL side graph
                self.control_live_panel.add_plot_sample(
                    live_time_s=live_time_s,
                    sensor_1_voltage=sensor_1_voltage,
                    sensor_2_voltage=sensor_2_voltage,
                )

                # SEQUENCE side graph
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
    # CAMERA CONTROL
    # =================================================================

    def _set_camera_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Toggle the camera on or off without impacting sensor sampling or CSV logging."""

        enabled = bool(enabled)
        self._camera_enabled = enabled

        if enabled:
            source_index = self.control_tab.get_camera_source_index()
            available = self.camera.open(source_index)
            self.logger.set_camera_available(available)
            if self.camera_2 is not None:
                try:
                    self.camera_2.open(1)
                except Exception:
                    pass
            if not available:
                self._camera_enabled = False
                self.control_tab.set_camera_state(False, config.CAMERA_NOT_AVAILABLE_TEXT)
                self.live_tab.set_camera_preview(None, False)
                self.live_tab.set_secondary_camera_preview(None, False)
                self._camera_preview_frame = None
                self._camera_error_logged = False
                return

            self.camera.refresh_camera_settings()
            self._camera_preview_frame = self.camera.get_preview_frame()
            self.control_tab.set_camera_state(True, config.CAMERA_ON_TEXT)
            self.control_tab.set_auto_exposure_enabled(
                self.camera.get_auto_exposure() if self.camera.supports_auto_exposure() else False,
                supported=self.camera.supports_auto_exposure(),
            )
            self.control_tab.set_exposure_value(
                self.camera.get_exposure() if self.camera.supports_exposure() else None,
                supported=self.camera.supports_exposure(),
            )
            self.control_tab.set_gain_value(
                self.camera.get_gain() if self.camera.supports_gain() else None,
                supported=self.camera.supports_gain(),
            )
            self.logger.set_camera_metadata(
                camera_index=self.camera.camera_index,
                camera_auto_exposure=self.camera.get_auto_exposure() if self.camera.supports_auto_exposure() else None,
                camera_exposure=self.camera.get_exposure() if self.camera.supports_exposure() else None,
                camera_gain=self.camera.get_gain() if self.camera.supports_gain() else None,
            )
            self._camera_error_logged = False
            self._update_camera_dropdowns()
            return

        self._stop_camera_video()
        self._camera_preview_frame = None
        self._camera_enabled = False
        self.camera.close()
        if self.camera_2 is not None:
            try:
                self.camera_2.close()
            except Exception:
                pass
        self.logger.set_camera_available(False)
        self.control_tab.set_camera_state(False, config.CAMERA_OFF_TEXT)
        self.control_tab.set_auto_exposure_enabled(False, supported=False)
        self.control_tab.set_exposure_value(None, supported=False)
        self.control_tab.set_gain_value(None, supported=False)
        self.live_tab.set_camera_preview(None, False)
        self.live_tab.set_secondary_camera_preview(None, False)
        self._update_camera_dropdowns()

    def _set_camera_2_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Toggle the secondary camera on or off without impacting the primary camera."""

        enabled = bool(enabled)
        self._camera_2_enabled = enabled

        if enabled:
            source_index = self.control_tab.get_camera_2_source_index()
            available = self.camera_2.open(source_index)
            if not available:
                self._camera_2_enabled = False
                self.control_tab.set_camera_2_state(False, config.CAMERA_NOT_AVAILABLE_TEXT)
                self.control_tab.set_camera_2_auto_exposure_enabled(False, supported=False)
                self.control_tab.set_camera_2_exposure_value(None, supported=False)
                self.control_tab.set_camera_2_gain_value(None, supported=False)
                self.live_tab.set_secondary_camera_preview(None, False)
                return

            self.camera_2.refresh_camera_settings()
            self.control_tab.set_camera_2_state(True, config.CAMERA_ON_TEXT)
            self.control_tab.set_camera_2_auto_exposure_enabled(
                self.camera_2.get_auto_exposure() if self.camera_2.supports_auto_exposure() else False,
                supported=self.camera_2.supports_auto_exposure(),
            )
            self.control_tab.set_camera_2_exposure_value(
                self.camera_2.get_exposure() if self.camera_2.supports_exposure() else None,
                supported=self.camera_2.supports_exposure(),
            )
            self.control_tab.set_camera_2_gain_value(
                self.camera_2.get_gain() if self.camera_2.supports_gain() else None,
                supported=self.camera_2.supports_gain(),
            )
            self._update_secondary_camera_preview()
            self._update_camera_dropdowns()
            return

        self.camera_2.close()
        self._camera_2_enabled = False
        self.control_tab.set_camera_2_state(False, config.CAMERA_OFF_TEXT)
        self.control_tab.set_camera_2_auto_exposure_enabled(False, supported=False)
        self.control_tab.set_camera_2_exposure_value(None, supported=False)
        self.control_tab.set_camera_2_gain_value(None, supported=False)
        self.live_tab.set_secondary_camera_preview(None, False)
        self._update_camera_dropdowns()

    def _set_camera_source(
        self,
        camera_index: int,
    ) -> None:
        """Select or switch camera source safely.

        Selecting a source while Camera is OFF only changes the preferred
        index; it must not silently open the webcam.
        """

        try:
            selected_index = int(camera_index)
            if self.camera is None:
                return

            if not self._camera_enabled:
                self.camera.camera_index = selected_index
                self.logger.set_camera_metadata(camera_index=selected_index)
                return

            switched = self.camera.set_camera_index(selected_index)
            if not switched:
                self._camera_enabled = False
                self.control_tab.set_camera_state(False, config.CAMERA_NOT_AVAILABLE_TEXT)
                self.control_tab.set_auto_exposure_enabled(False, supported=False)
                self.control_tab.set_exposure_value(None, supported=False)
                self.control_tab.set_gain_value(None, supported=False)
                self.live_tab.set_camera_preview(None, False)
                self.logger.set_camera_available(False)
                return

            self.camera.refresh_camera_settings()
            self._camera_preview_frame = self.camera.get_preview_frame()
            self.control_tab.set_camera_state(True, config.CAMERA_ON_TEXT)
            self.control_tab.set_auto_exposure_enabled(
                self.camera.get_auto_exposure() or False,
                supported=self.camera.supports_auto_exposure(),
            )
            self.control_tab.set_exposure_value(
                self.camera.get_exposure(),
                supported=self.camera.supports_exposure(),
            )
            self.control_tab.set_gain_value(
                self.camera.get_gain(),
                supported=self.camera.supports_gain(),
            )
            self.logger.set_camera_available(True)
            self.logger.set_camera_metadata(
                camera_index=self.camera.camera_index,
                camera_auto_exposure=self.camera.get_auto_exposure(),
                camera_exposure=self.camera.get_exposure(),
                camera_gain=self.camera.get_gain(),
            )
        except Exception:
            self._camera_enabled = False
            self.control_tab.set_camera_state(False, config.CAMERA_NOT_AVAILABLE_TEXT)
            self.control_tab.set_auto_exposure_enabled(False, supported=False)
            self.control_tab.set_exposure_value(None, supported=False)
            self.control_tab.set_gain_value(None, supported=False)
            self.live_tab.set_camera_preview(None, False)
            self.logger.set_camera_available(False)

    def _set_camera_2_source(
        self,
        camera_index: int,
    ) -> None:
        """Select or switch the secondary camera source."""

        try:
            selected_index = int(camera_index)
            if self.camera_2 is None:
                return

            if not self._camera_2_enabled:
                self.camera_2.camera_index = selected_index
                return

            switched = self.camera_2.set_camera_index(selected_index)
            if not switched:
                self._camera_2_enabled = False
                self.control_tab.set_camera_2_state(False, config.CAMERA_NOT_AVAILABLE_TEXT)
                self.control_tab.set_camera_2_auto_exposure_enabled(False, supported=False)
                self.control_tab.set_camera_2_exposure_value(None, supported=False)
                self.control_tab.set_camera_2_gain_value(None, supported=False)
                self.live_tab.set_secondary_camera_preview(None, False)
                return

            self.camera_2.refresh_camera_settings()
            self.control_tab.set_camera_2_state(True, config.CAMERA_ON_TEXT)
            self.control_tab.set_camera_2_auto_exposure_enabled(
                self.camera_2.get_auto_exposure() or False,
                supported=self.camera_2.supports_auto_exposure(),
            )
            self.control_tab.set_camera_2_exposure_value(
                self.camera_2.get_exposure(),
                supported=self.camera_2.supports_exposure(),
            )
            self.control_tab.set_camera_2_gain_value(
                self.camera_2.get_gain(),
                supported=self.camera_2.supports_gain(),
            )
            self._update_secondary_camera_preview()
        except Exception:
            self._camera_2_enabled = False
            self.control_tab.set_camera_2_state(False, config.CAMERA_NOT_AVAILABLE_TEXT)
            self.control_tab.set_camera_2_auto_exposure_enabled(False, supported=False)
            self.control_tab.set_camera_2_exposure_value(None, supported=False)
            self.control_tab.set_camera_2_gain_value(None, supported=False)
            self.live_tab.set_secondary_camera_preview(None, False)

    def _set_camera_auto_exposure(
        self,
        enabled: bool,
    ) -> None:
        """Apply auto exposure and synchronize GUI to driver readback."""

        if self.camera is None or not self._camera_enabled:
            return

        try:
            supported = self.camera.supports_auto_exposure()
            if not supported:
                self.control_tab.set_auto_exposure_enabled(False, supported=False)
                return

            self.camera.set_auto_exposure(bool(enabled))
            self.control_tab.set_auto_exposure_enabled(bool(enabled), supported=True)
            self.control_tab.set_exposure_value(
                self.camera.get_exposure(),
                supported=self.camera.supports_exposure(),
            )
            self.control_tab.set_gain_value(
                self.camera.get_gain(),
                supported=self.camera.supports_gain(),
            )
            self.logger.set_camera_metadata(
                camera_auto_exposure=bool(enabled),
                camera_exposure=self.camera.get_exposure(),
                camera_gain=self.camera.get_gain(),
            )
        except Exception:
            # Camera settings are non-critical; keep the rest of the testbench alive.
            pass

    def _set_camera_exposure(
        self,
        value: int,
    ) -> None:
        """Apply a manual exposure value and show the driver's actual value."""

        if self.camera is None or not self._camera_enabled:
            return

        try:
            supported = self.camera.supports_exposure()
            if not supported:
                self.control_tab.set_exposure_value(None, supported=False)
                return

            self.camera.set_exposure(int(value))
            actual = self.camera.get_exposure()
            self.control_tab.set_exposure_value(actual, supported=True)
            self.logger.set_camera_metadata(
                camera_auto_exposure=self.camera.get_auto_exposure(),
                camera_exposure=actual,
                camera_gain=self.camera.get_gain(),
            )
        except Exception:
            pass

    def _set_camera_2_auto_exposure(
        self,
        enabled: bool,
    ) -> None:
        """Apply auto exposure for the secondary camera."""

        if self.camera_2 is None or not self._camera_2_enabled:
            return

        try:
            supported = self.camera_2.supports_auto_exposure()
            if not supported:
                self.control_tab.set_camera_2_auto_exposure_enabled(False, supported=False)
                return

            self.camera_2.set_auto_exposure(bool(enabled))
            self.control_tab.set_camera_2_auto_exposure_enabled(bool(enabled), supported=True)
            self.control_tab.set_camera_2_exposure_value(
                self.camera_2.get_exposure(),
                supported=self.camera_2.supports_exposure(),
            )
            self.control_tab.set_camera_2_gain_value(
                self.camera_2.get_gain(),
                supported=self.camera_2.supports_gain(),
            )
        except Exception:
            pass

    def _set_camera_2_exposure(
        self,
        value: int,
    ) -> None:
        """Apply a manual exposure value to the secondary camera."""

        if self.camera_2 is None or not self._camera_2_enabled:
            return

        try:
            supported = self.camera_2.supports_exposure()
            if not supported:
                self.control_tab.set_camera_2_exposure_value(None, supported=False)
                return

            self.camera_2.set_exposure(int(value))
            actual = self.camera_2.get_exposure()
            self.control_tab.set_camera_2_exposure_value(actual, supported=True)
        except Exception:
            pass

    def _set_camera_gain(
        self,
        value: int,
    ) -> None:
        """Apply a manual gain value and show the driver's actual value."""

        if self.camera is None or not self._camera_enabled:
            return

        try:
            supported = self.camera.supports_gain()
            if not supported:
                self.control_tab.set_gain_value(None, supported=False)
                return

            self.camera.set_gain(int(value))
            actual = self.camera.get_gain()
            self.control_tab.set_gain_value(actual, supported=True)
            self.logger.set_camera_metadata(
                camera_auto_exposure=self.camera.get_auto_exposure(),
                camera_exposure=self.camera.get_exposure(),
                camera_gain=actual,
            )
        except Exception:
            pass

    def _set_camera_2_gain(
        self,
        value: int,
    ) -> None:
        """Apply a manual gain value to the secondary camera."""

        if self.camera_2 is None or not self._camera_2_enabled:
            return

        try:
            supported = self.camera_2.supports_gain()
            if not supported:
                self.control_tab.set_camera_2_gain_value(None, supported=False)
                return

            self.camera_2.set_gain(int(value))
            actual = self.camera_2.get_gain()
            self.control_tab.set_camera_2_gain_value(actual, supported=True)
        except Exception:
            pass

    def _set_record_video(
        self,
        enabled: bool,
    ) -> None:
        """Set whether the next manual/sequence recording should include video."""

        self._camera_record_video = bool(enabled)

    def _set_camera_2_record_video(
        self,
        enabled: bool,
    ) -> None:
        """Set whether camera 2 should capture video during the next recording."""

        self._camera_2_record_video = bool(enabled)

    def _update_secondary_camera_preview(
        self,
    ) -> None:
        """Optional second USB preview kept independent of the primary camera logic."""

        if self.camera_2 is None:
            self.live_tab.set_secondary_camera_preview(None, False)
            return

        try:
            frame = self.camera_2.get_preview_frame()
            available = self.camera_2.is_available()
            self.live_tab.set_secondary_camera_preview(frame, available)
        except Exception:
            self.live_tab.set_secondary_camera_preview(None, False)

    def _update_camera_state(
        self,
    ) -> None:
        """Refresh preview/status only. Video writing is worker-owned."""

        if self.camera is not None and self._camera_enabled:
            try:
                frame = self.camera.get_preview_frame()
                available = self.camera.is_available()
                self.logger.set_camera_available(available)
                self._camera_preview_frame = frame
                self.live_tab.set_camera_preview(frame, available)
            except Exception:
                self.logger.set_camera_available(False)
                self.live_tab.set_camera_preview(None, False)
                self._camera_enabled = False
                self.control_tab.set_camera_state(False, config.CAMERA_NOT_AVAILABLE_TEXT)

        elif self.camera is not None:
            self.live_tab.set_camera_preview(None, False)

        if self.camera_2 is not None and self._camera_2_enabled:
            try:
                self._update_secondary_camera_preview()
            except Exception:
                self.live_tab.set_secondary_camera_preview(None, False)
        elif self.camera_2 is not None:
            self.live_tab.set_secondary_camera_preview(None, False)

        if self.camera is not None and self._camera_enabled and self._camera_recording_active:
            try:
                recording_error = self.camera.get_recording_error()
                if recording_error:
                    self._camera_recording_active = False
                    if self.logger.is_recording() and not self._camera_error_logged:
                        self.logger.log_event(
                            "camera_error",
                            {"video_recording": recording_error},
                        )
                        self._camera_error_logged = True
            except Exception:
                pass

    def _start_camera_video(
        self,
    ) -> None:
        """Start writing companion MP4s for any active camera whose video flag is enabled."""

        if self.camera is not None and self._camera_enabled and self._camera_record_video:
            try:
                video_path = self.logger.get_video_path()
                if video_path is None:
                    video_path = self.logger.build_video_path()
                    self.logger._video_path = video_path

                if self.camera.start_recording(video_path):
                    self._camera_recording_active = True
                    self._camera_error_logged = False
                    self.logger.log_event("video_recording_started", video_path.name)
                    self.logger.set_camera_available(True)
                    self.logger.set_camera_metadata(
                        camera_index=self.camera.camera_index,
                        camera_auto_exposure=self.camera.get_auto_exposure(),
                        camera_exposure=self.camera.get_exposure(),
                        camera_gain=self.camera.get_gain(),
                        video_recorded=True,
                    )
                else:
                    self.logger.log_event("camera_error", "video_start_failed")
                    self._camera_recording_active = False
            except Exception:
                self._camera_recording_active = False
                try:
                    self.logger.log_event("camera_error", "video_start_failed")
                except Exception:
                    pass

        if self.camera_2 is not None and self._camera_2_enabled and self._camera_2_record_video:
            try:
                video_path = self.logger.get_video_path()
                if video_path is None:
                    video_path = self.logger.build_video_path()
                    self.logger._video_path = video_path

                if self.camera_2.start_recording(video_path):
                    self.logger.log_event("video_recording_started_camera_2", video_path.name)
                    self.logger.set_camera_available(True)
            except Exception:
                try:
                    self.logger.log_event("camera_error", "video_start_failed_camera_2")
                except Exception:
                    pass

    def _stop_camera_video(
        self,
    ) -> None:
        """Stop active video capture safely without affecting CSV or sequence logic."""

        if self.camera is None:
            return

        try:
            if self._camera_recording_active:
                self.camera.stop_recording()
                self._camera_recording_active = False
                if self.logger.is_recording():
                    self.logger.log_event("video_recording_stopped", self.logger.get_video_path().name if self.logger.get_video_path() else "")
        except Exception:
            pass
        finally:
            self._camera_recording_active = False

    # =================================================================
    # LIVE PLOT CONTROL
    # =================================================================

    def _set_live_plot_enabled(
        self,
        enabled: bool,
    ) -> None:
        """
        Enable or freeze graph updates.

        This affects graph display only.

        It does NOT:
            - Stop sensor reads
            - Stop live voltage labels
            - Stop CSV recording
            - Stop or change a sequence
        """

        enabled = bool(
            enabled
        )

        if enabled == self._live_plot_enabled:

            self._update_live_plot_status()

            return

        now = time.monotonic()

        if enabled:

            # Resume graph clock without counting frozen duration.
            if self._live_plot_paused_at_monotonic is not None:

                self._live_plot_paused_total_s += (
                    now
                    - self._live_plot_paused_at_monotonic
                )

                self._live_plot_paused_at_monotonic = None

        else:

            # Freeze graph clock at the current graph time.
            self._live_plot_paused_at_monotonic = (
                now
            )

        self._live_plot_enabled = enabled

        self._update_live_plot_status()

    def _get_live_plot_time_s(
        self,
    ) -> float:
        """
        Return pause-aware live graph time.

        Frozen periods are excluded so the X-axis continues smoothly
        when plotting resumes.
        """

        if self._live_plot_paused_at_monotonic is not None:

            now = (
                self._live_plot_paused_at_monotonic
            )

        else:

            now = time.monotonic()

        elapsed = (
            now
            - self._live_start_monotonic
            - self._live_plot_paused_total_s
        )

        return max(
            0.0,
            float(elapsed),
        )

    def _update_live_plot_status(
        self,
    ) -> None:
        """Synchronize plot state across CONTROL and side panels."""

        self.control_tab.set_live_plot_enabled(
            self._live_plot_enabled
        )

        self.control_live_panel.update_live_plot_status(
            self._live_plot_enabled
        )

        self.sequence_live_panel.update_live_plot_status(
            self._live_plot_enabled
        )

    def _apply_sequence_end_plot_behavior(
        self,
    ) -> None:
        """
        Apply selected sequence plot behavior.

        If selected, graphs freeze when the sequence ends.

        Sensors, numerical values and any manual recording continue.
        """

        if self._freeze_plot_after_sequence:

            self._set_live_plot_enabled(
                False
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
        """Enable or disable Sensor 1 and its LED."""

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
        """Enable or disable Sensor 2 and its LED."""

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
        Update manually logged smoke-machine state.

        This remains allowed while a sequence is running.
        """

        self.session.set_smoke_machine_active(
            active
        )

        self._log_state_change_events()

        self._update_gui()

    # =================================================================
    # MANUAL RECORDING
    # =================================================================

    def _start_recording(
        self,
    ) -> None:
        """Start manual recording from CONTROL."""

        if self.sequence.is_running():
            return

        if self.logger.is_recording():
            return

        metadata = (
            self.control_tab.get_test_metadata()
        )

        self.session.set_metadata(
            test_name=metadata[
                "test_name"
            ],
            mount_name=metadata[
                "mount_name"
            ],
            comment=metadata[
                "comment"
            ],
        )

        try:

            self.logger.start()

            if self._camera_enabled and self._camera_record_video:
                self._start_camera_video()

            # Manual recording ownership.
            self._recording_started_by_sequence = False

            self._last_event_state = (
                self._get_event_state_snapshot()
            )

            # ---------------------------------------------------------
            # New recording = fresh visual graph timeline.
            #
            # Plot state itself is NOT changed here.
            # If user has manually frozen the graph, it remains frozen.
            # ---------------------------------------------------------

            self._reset_live_plots()

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

    def _stop_recording(
        self,
    ) -> None:
        """Stop manual recording."""

        if self.sequence.is_running():
            return

        if not self.logger.is_recording():
            return

        try:

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
            2. Check recording conflict
            3. Build sequence steps
            4. Enable live plotting
            5. Apply selected sensors
            6. Start sequence recording if selected
            7. Reset graph timeline to 0
            8. Start sequence
            9. Add Step 1 marker
            10. Lock controls

        An unrecorded sequence may run while a manual recording is
        active. The manual recording continues unchanged.
        """

        if self.sequence.is_running():
            return

        record_sequence = (
            self.sequence_tab.get_record_sequence()
        )

        freeze_plot_after_sequence = (
            self.sequence_tab.get_freeze_plot_after_sequence()
        )

        previous_live_plot_enabled = (
            self._live_plot_enabled
        )

        # -------------------------------------------------------------
        # Recorded sequence cannot start if another recording exists.
        # -------------------------------------------------------------

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
                    "starting a sequence with "
                    "'Record sequence' enabled."
                ),
            )

            return

        try:

            # ---------------------------------------------------------
            # Convert GUI rows to SequenceStep objects
            # ---------------------------------------------------------

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

            # Capture this run's plot behavior.
            self._freeze_plot_after_sequence = bool(
                freeze_plot_after_sequence
            )

            # ---------------------------------------------------------
            # Every sequence begins with plotting ON.
            #
            # This ensures a previously frozen graph never causes an
            # automatic test to run without being shown.
            # ---------------------------------------------------------

            self._set_live_plot_enabled(
                True
            )

            # ---------------------------------------------------------
            # Apply sequence sensor selection
            # ---------------------------------------------------------

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

            self._log_state_change_events()

            # ---------------------------------------------------------
            # Optional sequence-owned recording
            # ---------------------------------------------------------

            if record_sequence:

                metadata = (
                    self.sequence_tab.get_test_metadata()
                )

                self.session.set_metadata(
                    test_name=metadata[
                        "test_name"
                    ],
                    mount_name=metadata[
                        "mount_name"
                    ],
                    comment=metadata[
                        "comment"
                    ],
                )

                self.logger.start()

                if self._camera_enabled and self.sequence_tab.get_record_video():
                    self._camera_record_video = True
                    self._start_camera_video()

                self._recording_started_by_sequence = True

                self._last_event_state = (
                    self._get_event_state_snapshot()
                )

            # ---------------------------------------------------------
            # EVERY sequence starts a fresh graph at 0 s.
            # ---------------------------------------------------------

            self._reset_live_plots()

            # ---------------------------------------------------------
            # Start sequence
            # ---------------------------------------------------------

            self.sequence.start()

            self._log_state_change_events()

            # ---------------------------------------------------------
            # Step 1 marker at graph origin
            # ---------------------------------------------------------

            current_step = (
                self.sequence.get_current_step_number()
            )

            if current_step is not None:

                self.live_tab.add_sequence_step_marker(
                    live_time_s=0.0,
                    step_number=current_step,
                )

                self._last_sequence_step = (
                    current_step
                )

            # ---------------------------------------------------------
            # Sequence-start event
            # ---------------------------------------------------------

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

            # ---------------------------------------------------------
            # Lock interfaces
            # ---------------------------------------------------------

            self.control_tab.set_sequence_running(
                True
            )

            self.sequence_tab.set_sequence_running(
                True
            )

            self._update_gui()

        except Exception as exc:

            # ---------------------------------------------------------
            # Roll back sequence-owned recording if startup failed.
            # ---------------------------------------------------------

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

            self._freeze_plot_after_sequence = False

            # Restore previous manual plot state.
            self._set_live_plot_enabled(
                previous_live_plot_enabled
            )

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

    def _stop_sequence(
        self,
    ) -> None:
        """Stop sequence from SEQUENCE tab."""

        if not self.sequence.is_running():
            return

        try:

            self.sequence.stop()

            self._log_state_change_events()

            if self.logger.is_recording():

                self.logger.log_event(
                    "sequence_stopped",
                    "manual",
                )

            if (
                self._recording_started_by_sequence
                and self.logger.is_recording()
            ):

                if self._camera_recording_active:
                    self._stop_camera_video()

                self.logger.stop()

            self._recording_started_by_sequence = False

            self.control_tab.set_sequence_running(
                False
            )

            self.sequence_tab.set_sequence_running(
                False
            )

            # Apply selected Freeze-after-sequence behavior.
            self._apply_sequence_end_plot_behavior()

            self._freeze_plot_after_sequence = False

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
        Handle normal sequence completion.

        SequenceController has already:
            - stopped both fans
            - set PWM to zero
            - marked sequence_running False
        """

        self._log_state_change_events()

        if self.logger.is_recording():

            self.logger.log_event(
                "sequence_completed"
            )

        # -------------------------------------------------------------
        # Only sequence-owned recording stops.
        #
        # Manual recording continues after an unrecorded sequence.
        # -------------------------------------------------------------

        if (
            self._recording_started_by_sequence
            and self.logger.is_recording()
        ):

            if self._camera_recording_active:
                self._stop_camera_video()

            self.logger.stop()

        self._recording_started_by_sequence = False

        self.control_tab.set_sequence_running(
            False
        )

        self.sequence_tab.set_sequence_running(
            False
        )

        # -------------------------------------------------------------
        # Freeze graph if selected for this sequence.
        # -------------------------------------------------------------

        self._apply_sequence_end_plot_behavior()

        self._freeze_plot_after_sequence = False

        self._update_gui()

    # =================================================================
    # STOP ALL
    # =================================================================

    def _stop_all(
        self,
    ) -> None:
        """
        STOP ALL safety action.

        Always:
            - Stop Main Fan
            - Main PWM -> 0 %
            - Stop Smoke Fan
            - Smoke PWM -> 0 %
            - Stop sequence

        Never:
            - Disable sensors
            - Change smoke-machine state

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

            # ---------------------------------------------------------
            # Stop sequence / fans
            # ---------------------------------------------------------

            if sequence_was_running:

                self.sequence.stop()

            else:

                self.main_fan.stop()

                self.smoke_fan.stop()

            self.session.apply_stop_all_state()

            # ---------------------------------------------------------
            # Log resulting fan changes
            # ---------------------------------------------------------

            self._log_state_change_events()

            # ---------------------------------------------------------
            # Explicit events
            # ---------------------------------------------------------

            if self.logger.is_recording():

                if sequence_was_running:

                    self.logger.log_event(
                        "sequence_stopped",
                        "stop_all",
                    )

                self.logger.log_event(
                    "stop_all"
                )

            # ---------------------------------------------------------
            # Recording ownership
            # ---------------------------------------------------------

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

            # If STOP ALL ended an active sequence, respect the sequence
            # option for freezing the completed/aborted graph.
            if sequence_was_running:

                self._apply_sequence_end_plot_behavior()

                self._freeze_plot_after_sequence = False

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
        """Return discrete states used for event detection."""

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

    # =================================================================
    # EVENT LOGGING
    # =================================================================

    def _log_state_change_events(
        self,
    ) -> None:
        """
        Detect discrete state changes and write event records.

        Snapshot is updated even if recording is not active.

        This prevents changes made before recording from appearing
        as new events after recording starts.
        """

        current = (
            self._get_event_state_snapshot()
        )

        previous = (
            self._last_event_state
        )

        if self.logger.is_recording():

            # ---------------------------------------------------------
            # Main fan ON/OFF
            # ---------------------------------------------------------

            if (
                current["main_fan_active"]
                != previous["main_fan_active"]
            ):

                self.logger.log_event(
                    (
                        "main_fan_on"
                        if current[
                            "main_fan_active"
                        ]
                        else "main_fan_off"
                    )
                )

            # ---------------------------------------------------------
            # Main fan PWM
            # ---------------------------------------------------------

            if (
                current["main_fan_pwm_percent"]
                != previous[
                    "main_fan_pwm_percent"
                ]
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

            # ---------------------------------------------------------
            # Smoke fan ON/OFF
            # ---------------------------------------------------------

            if (
                current["smoke_fan_active"]
                != previous["smoke_fan_active"]
            ):

                self.logger.log_event(
                    (
                        "smoke_fan_on"
                        if current[
                            "smoke_fan_active"
                        ]
                        else "smoke_fan_off"
                    )
                )

            # ---------------------------------------------------------
            # Smoke fan PWM
            # ---------------------------------------------------------

            if (
                current[
                    "smoke_fan_pwm_percent"
                ]
                != previous[
                    "smoke_fan_pwm_percent"
                ]
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

            # ---------------------------------------------------------
            # Smoke machine
            # ---------------------------------------------------------

            if (
                current[
                    "smoke_machine_active"
                ]
                != previous[
                    "smoke_machine_active"
                ]
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

            # ---------------------------------------------------------
            # Sensor 1
            # ---------------------------------------------------------

            if (
                current["sensor_1_active"]
                != previous["sensor_1_active"]
            ):

                self.logger.log_event(
                    (
                        "sensor_1_on"
                        if current[
                            "sensor_1_active"
                        ]
                        else "sensor_1_off"
                    )
                )

            # ---------------------------------------------------------
            # Sensor 2
            # ---------------------------------------------------------

            if (
                current["sensor_2_active"]
                != previous["sensor_2_active"]
            ):

                self.logger.log_event(
                    (
                        "sensor_2_on"
                        if current[
                            "sensor_2_active"
                        ]
                        else "sensor_2_off"
                    )
                )

        self._last_event_state = (
            current
        )

    # =================================================================
    # PLOT HELPERS
    # =================================================================

    def _clear_all_plots(
        self,
    ) -> None:
        """
        Clear:
            - LIVE DATA graph
            - CONTROL mini graph
            - SEQUENCE mini graph
        """

        self.live_tab.clear_plots()

        self.control_live_panel.clear_plots()

        self.sequence_live_panel.clear_plots()

    def _reset_live_plots(
        self,
    ) -> None:
        """
        Clear all live graphs and reset GUI live time to zero.

        If plotting is currently frozen, graph time remains paused at
        0 s until plotting is enabled again.

        IMPORTANT:
        This does NOT change:
            - logger state
            - CSV timestamps
            - recording elapsed time
            - TestSession recording timing
        """

        now = time.monotonic()

        self._live_start_monotonic = (
            now
        )

        self._live_plot_paused_total_s = 0.0

        if self._live_plot_enabled:

            self._live_plot_paused_at_monotonic = None

        else:

            self._live_plot_paused_at_monotonic = (
                now
            )

        self._last_sequence_step = None

        self._clear_all_plots()

    # =================================================================
    # GUI SYNCHRONIZATION
    # =================================================================

    def _update_gui(
        self,
    ) -> None:
        """Synchronize all displays with TestSession."""

        sequence_running = (
            self.sequence.is_running()
        )

        # -------------------------------------------------------------
        # CONTROL
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Live plot state
        # -------------------------------------------------------------

        self._update_live_plot_status()

        # -------------------------------------------------------------
        # SEQUENCE
        # -------------------------------------------------------------

        self.sequence_tab.set_sequence_running(
            sequence_running
        )

        self.sequence_tab.set_smoke_machine_active(
            self.session.smoke_machine_active
        )

        # -------------------------------------------------------------
        # Shared sensor data
        # -------------------------------------------------------------

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

        self.control_tab.update_sensor_values(
            **sensor_kwargs
        )

        # -------------------------------------------------------------
        # Shared fan data
        # -------------------------------------------------------------

        fan_kwargs = {

            "main_fan_active":
                self.session.main_fan_active,

            "main_fan_pwm_percent":
                self.session.main_fan_pwm_percent,

            "smoke_fan_active":
                self.session.smoke_fan_active,

            "smoke_fan_pwm_percent":
                self.session.smoke_fan_pwm_percent,

            "main_fan_rpm": self.session.main_fan_rpm,
            "smoke_fan_rpm": self.session.smoke_fan_rpm,
        }

        # -------------------------------------------------------------
        # Shared experiment state
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Update display-only panels
        # -------------------------------------------------------------

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

        Timer stops and fan outputs are placed in safe state.
        """

        if hasattr(
            self,
            "update_timer",
        ):

            self.update_timer.stop()

        # -------------------------------------------------------------
        # Stop sequence
        # -------------------------------------------------------------

        try:

            if self.sequence.is_running():

                self.sequence.stop()

        except Exception:

            pass

        # -------------------------------------------------------------
        # Stop fans
        # -------------------------------------------------------------

        try:

            self.main_fan.stop()

        except Exception:

            pass

        try:

            self.smoke_fan.stop()

        except Exception:

            pass

        # -------------------------------------------------------------
        # Synchronize session
        # -------------------------------------------------------------

        self.session.apply_stop_all_state()

        # -------------------------------------------------------------
        # Preserve recording file if possible
        # -------------------------------------------------------------

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

    # =================================================================
    # ERROR DIALOG
    # =================================================================

    @staticmethod
    def _show_error(
        title: str,
        exception: Exception,
    ) -> None:
        """Display critical-error dialog."""

        QMessageBox.critical(
            None,
            title,
            str(exception),
        )

    # =================================================================
    # CLEANUP
    # =================================================================

    def cleanup(
        self,
    ) -> None:
        """Safely shut down complete application."""

        if self._cleanup_done:
            return

        self._cleanup_done = True

        # -------------------------------------------------------------
        # Timer
        # -------------------------------------------------------------

        if hasattr(
            self,
            "update_timer",
        ):

            self.update_timer.stop()

        if hasattr(
            self,
            "camera_timer",
        ):

            self.camera_timer.stop()

        # -------------------------------------------------------------
        # Camera
        # -------------------------------------------------------------

        try:
            self._stop_camera_video()
            if self.camera is not None:
                self.camera.close()
        except Exception:
            pass

        # -------------------------------------------------------------
        # Logger
        # -------------------------------------------------------------

        try:

            if self.logger.is_recording():

                self.logger.log_event(
                    "application_closed"
                )

            self.logger.cleanup()

        except Exception:

            pass

        # -------------------------------------------------------------
        # Sequence
        # -------------------------------------------------------------

        try:

            self.sequence.cleanup()

        except Exception:

            pass

        # -------------------------------------------------------------
        # Sensors
        # -------------------------------------------------------------

        try:

            self.sensor_1.cleanup()

        except Exception:

            pass

        try:

            self.sensor_2.cleanup()

        except Exception:

            pass

        # -------------------------------------------------------------
        # FG / RPM monitors
        # -------------------------------------------------------------

        for monitor in (
            getattr(self, "main_fan_rpm_monitor", None),
            getattr(self, "smoke_fan_rpm_monitor", None),
        ):
            if monitor is not None:
                try:
                    monitor.cleanup()
                except Exception:
                    pass

        # -------------------------------------------------------------
        # Fans
        # -------------------------------------------------------------

        try:

            self.main_fan.cleanup()

        except Exception:

            pass

        try:

            self.smoke_fan.cleanup()

        except Exception:

            pass

        # -------------------------------------------------------------
        # LEDs
        # -------------------------------------------------------------

        try:

            self.sensor_1_led.cleanup()

        except Exception:

            pass

        try:

            self.sensor_2_led.cleanup()

        except Exception:

            pass

        # -------------------------------------------------------------
        # ADC
        # -------------------------------------------------------------

        try:

            self.adc.close()

        except Exception:

            pass

    # =================================================================
    # WINDOW CLOSE
    # =================================================================

    def closeEvent(
        self,
        event,
    ) -> None:
        """Qt window-close event."""

        self.cleanup()

        event.accept()