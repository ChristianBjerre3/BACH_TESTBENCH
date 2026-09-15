"""
gui/control_tab.py

Manual CONTROL interface for the Airflow Smoke Test Bench.

CONTROL is the manual workflow.

Available functionality:
    - Test name
    - Mount
    - Comment
    - Main fan ON/OFF
    - Main fan PWM
    - Smoke fan ON/OFF
    - Smoke fan PWM
    - Sensor 1 ON/OFF
    - Sensor 2 ON/OFF
    - Sensor 1 live voltage
    - Sensor 2 live voltage
    - Manual smoke-machine ON/OFF logging
    - Manual recording start/stop
    - Live plot ON/OFF
    - STOP ALL

IMPORTANT:
Live plot only controls whether graphs receive new samples.

Turning Live plot OFF does NOT:
    - Disable sensors
    - Stop ADC readings
    - Stop live voltage values
    - Stop CSV recording
    - Stop a sequence

This module contains GUI behavior only.
It does not directly access hardware.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QSizePolicy,
    QSpinBox,
)

import config

from gui.styles import (
    set_card,
    set_role,
    set_label_role,
    CARD_SPACING,
    PAGE_MARGIN,
)


class ControlTab(QWidget):
    """Manual test/control interface."""

    # =================================================================
    # SIGNALS
    # =================================================================

    main_fan_active_changed = Signal(bool)
    main_fan_pwm_changed = Signal(int)

    smoke_fan_active_changed = Signal(bool)
    smoke_fan_pwm_changed = Signal(int)

    smoke_machine_active_changed = Signal(bool)

    sensor_1_active_changed = Signal(bool)
    sensor_2_active_changed = Signal(bool)

    start_recording_requested = Signal()
    stop_recording_requested = Signal()

    camera_enabled_changed = Signal(bool)
    camera_source_changed = Signal(int)
    auto_exposure_changed = Signal(bool)
    exposure_changed = Signal(int)
    gain_changed = Signal(int)
    record_video_changed = Signal(bool)

    stop_all_requested = Signal()

    # New display-only control.
    live_plot_enabled_changed = Signal(bool)

    # =================================================================
    # INITIALIZATION
    # =================================================================

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._sequence_running = False
        self._recording = False
        self._camera_enabled = False
        self._record_video = False

        # Camera-property capability/state is kept explicitly.  Do not infer
        # support from a widget's current enabled state, because that can make
        # a temporarily disabled control stay disabled forever.
        self._camera_auto_exposure_supported = False
        self._camera_exposure_supported = False
        self._camera_gain_supported = False
        self._camera_auto_exposure = True

        self._live_plot_enabled = True

        self._sensor_1_voltage: Optional[float] = None
        self._sensor_2_voltage: Optional[float] = None

        self._build_ui()
        self._connect_internal_signals()
        self._set_initial_state()

    # =================================================================
    # BUILD UI
    # =================================================================

    def _build_ui(self) -> None:
        """
        Build CONTROL dashboard.

        Layout:

        ┌──────────────────────┬──────────────────────┐
        │ TEST INFORMATION     │ MAIN FAN             │
        ├──────────────────────┼──────────────────────┤
        │ SENSOR 1             │ SMOKE FAN            │
        ├──────────────────────┼──────────────────────┤
        │ SENSOR 2             │ SMOKE MACHINE        │
        ├──────────────────────┴──────────────────────┤
        │ RECORDING / LIVE PLOT                       │
        └─────────────────────────────────────────────┘

        STOP ALL is moved to the right-side column by MainWindow.
        """

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            PAGE_MARGIN,
            PAGE_MARGIN,
            PAGE_MARGIN,
            PAGE_MARGIN,
        )

        main_layout.setSpacing(
            CARD_SPACING
        )

        # -------------------------------------------------------------
        # Sequence lock banner
        # -------------------------------------------------------------

        self.sequence_lock_label = QLabel(
            "Automatic sequence running — manual controls are locked"
        )

        self.sequence_lock_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.sequence_lock_label.setProperty(
            "role",
            "statusRecording",
        )

        self.sequence_lock_label.setStyleSheet(
            """
            QLabel {
                background-color: #351824;
                border: 1px solid #7A2638;
                border-radius: 7px;
                padding: 8px;
            }
            """
        )

        self.sequence_lock_label.setVisible(
            False
        )

        main_layout.addWidget(
            self.sequence_lock_label
        )

        # -------------------------------------------------------------
        # Main two-column dashboard
        # -------------------------------------------------------------

        dashboard_layout = QGridLayout()

        dashboard_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        dashboard_layout.setHorizontalSpacing(
            CARD_SPACING
        )

        dashboard_layout.setVerticalSpacing(
            CARD_SPACING
        )

        self.metadata_card = (
            self._create_metadata_card()
        )

        self.sensor_1_card = (
            self._create_sensor_1_card()
        )

        self.sensor_2_card = (
            self._create_sensor_2_card()
        )

        self.main_fan_card = (
            self._create_main_fan_card()
        )

        self.smoke_fan_card = (
            self._create_smoke_fan_card()
        )

        self.smoke_machine_card = (
            self._create_smoke_machine_card()
        )

        # Left column
        dashboard_layout.addWidget(
            self.metadata_card,
            0,
            0,
        )

        dashboard_layout.addWidget(
            self.sensor_1_card,
            1,
            0,
        )

        dashboard_layout.addWidget(
            self.sensor_2_card,
            2,
            0,
        )

        # Right column
        dashboard_layout.addWidget(
            self.main_fan_card,
            0,
            1,
        )

        dashboard_layout.addWidget(
            self.smoke_fan_card,
            1,
            1,
        )

        dashboard_layout.addWidget(
            self.smoke_machine_card,
            2,
            1,
        )

        dashboard_layout.setColumnStretch(
            0,
            1,
        )

        dashboard_layout.setColumnStretch(
            1,
            1,
        )

        dashboard_layout.setRowStretch(
            0,
            2,
        )

        dashboard_layout.setRowStretch(
            1,
            1,
        )

        dashboard_layout.setRowStretch(
            2,
            1,
        )

        main_layout.addLayout(
            dashboard_layout,
            stretch=1,
        )

        # -------------------------------------------------------------
        # Recording + Live Plot
        # -------------------------------------------------------------

        self.recording_card = (
            self._create_recording_card()
        )

        self.camera_card = (
            self._create_camera_card()
        )

        main_layout.addWidget(
            self.recording_card
        )

        main_layout.addWidget(
            self.camera_card
        )

        # -------------------------------------------------------------
        # STOP ALL
        #
        # MainWindow removes this widget from this layout and places it
        # below the right-side live panel.
        # -------------------------------------------------------------

        self.stop_all_button = (
            self._create_stop_all_button()
        )

        main_layout.addWidget(
            self.stop_all_button
        )

    # =================================================================
    # CARD HELPERS
    # =================================================================

    @staticmethod
    def _new_card() -> QFrame:
        """Create standard dashboard card."""

        card = QFrame()

        card.setFrameShape(
            QFrame.Shape.NoFrame
        )

        set_card(
            card
        )

        return card

    @staticmethod
    def _create_card_title(
        text: str,
    ) -> QLabel:
        """Create standard card title."""

        label = QLabel(
            text.upper()
        )

        set_label_role(
            label,
            "cardTitle",
        )

        return label

    @staticmethod
    def _create_state_text(
        active: bool = False,
    ) -> QLabel:
        """Create ON/OFF status label."""

        label = QLabel(
            "ON"
            if active
            else "OFF"
        )

        label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        set_label_role(
            label,
            "statusOn"
            if active
            else "statusOff",
        )

        return label

    # =================================================================
    # METADATA CARD
    # =================================================================

    def _create_metadata_card(
        self,
    ) -> QFrame:
        """Create Test Information card."""

        card = self._new_card()

        layout = QVBoxLayout(
            card
        )

        layout.setContentsMargins(
            16,
            14,
            16,
            16,
        )

        layout.setSpacing(
            8
        )

        layout.addWidget(
            self._create_card_title(
                "Test Information"
            )
        )

        # Test name
        test_label = QLabel(
            "Test name"
        )

        set_label_role(
            test_label,
            "fieldLabel",
        )

        self.test_name_input = QLineEdit()

        self.test_name_input.setPlaceholderText(
            "Example: Test 01"
        )

        layout.addWidget(
            test_label
        )

        layout.addWidget(
            self.test_name_input
        )

        # Mount
        mount_label = QLabel(
            "Mount"
        )

        set_label_role(
            mount_label,
            "fieldLabel",
        )

        self.mount_name_input = QLineEdit()

        self.mount_name_input.setPlaceholderText(
            "Example: Mount A"
        )

        layout.addWidget(
            mount_label
        )

        layout.addWidget(
            self.mount_name_input
        )

        # Comment
        comment_label = QLabel(
            "Comment"
        )

        set_label_role(
            comment_label,
            "fieldLabel",
        )

        self.comment_input = QTextEdit()

        self.comment_input.setPlaceholderText(
            "Optional comment"
        )

        self.comment_input.setMaximumHeight(
            72
        )

        layout.addWidget(
            comment_label
        )

        layout.addWidget(
            self.comment_input
        )

        return card

    # =================================================================
    # SENSOR 1 CARD
    # =================================================================

    def _create_sensor_1_card(
        self,
    ) -> QFrame:
        """Create Sensor 1 card."""

        card = self._new_card()

        layout = QVBoxLayout(
            card
        )

        layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        layout.setSpacing(
            7
        )

        header = QHBoxLayout()

        header.addWidget(
            self._create_card_title(
                "Sensor 1"
            )
        )

        header.addStretch()

        self.sensor_1_state_label = (
            self._create_state_text()
        )

        header.addWidget(
            self.sensor_1_state_label
        )

        layout.addLayout(
            header
        )

        row = QHBoxLayout()

        self.sensor_1_button = QPushButton(
            "OFF"
        )

        self.sensor_1_button.setCheckable(
            True
        )

        set_role(
            self.sensor_1_button,
            "toggle",
        )

        self.sensor_1_voltage_label = QLabel(
            "-- V"
        )

        set_label_role(
            self.sensor_1_voltage_label,
            "liveValueSensor1",
        )

        self.sensor_1_voltage_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        row.addWidget(
            self.sensor_1_button
        )

        row.addStretch()

        row.addWidget(
            self.sensor_1_voltage_label
        )

        layout.addLayout(
            row
        )

        info = QLabel(
            "Optical sensor"
        )

        set_label_role(
            info,
            "muted",
        )

        layout.addWidget(
            info
        )

        return card

    # =================================================================
    # SENSOR 2 CARD
    # =================================================================

    def _create_sensor_2_card(
        self,
    ) -> QFrame:
        """Create Sensor 2 card."""

        card = self._new_card()

        layout = QVBoxLayout(
            card
        )

        layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        layout.setSpacing(
            7
        )

        header = QHBoxLayout()

        header.addWidget(
            self._create_card_title(
                "Sensor 2"
            )
        )

        header.addStretch()

        self.sensor_2_state_label = (
            self._create_state_text()
        )

        header.addWidget(
            self.sensor_2_state_label
        )

        layout.addLayout(
            header
        )

        row = QHBoxLayout()

        self.sensor_2_button = QPushButton(
            "OFF"
        )

        self.sensor_2_button.setCheckable(
            True
        )

        set_role(
            self.sensor_2_button,
            "toggle",
        )

        self.sensor_2_voltage_label = QLabel(
            "-- V"
        )

        set_label_role(
            self.sensor_2_voltage_label,
            "liveValueSensor2",
        )

        self.sensor_2_voltage_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        row.addWidget(
            self.sensor_2_button
        )

        row.addStretch()

        row.addWidget(
            self.sensor_2_voltage_label
        )

        layout.addLayout(
            row
        )

        info = QLabel(
            "Optical sensor"
        )

        set_label_role(
            info,
            "muted",
        )

        layout.addWidget(
            info
        )

        return card

    # =================================================================
    # MAIN FAN CARD
    # =================================================================

    def _create_main_fan_card(
        self,
    ) -> QFrame:
        """Create Main Fan card."""

        card = self._new_card()

        layout = QVBoxLayout(
            card
        )

        layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        layout.setSpacing(
            10
        )

        header = QHBoxLayout()

        header.addWidget(
            self._create_card_title(
                "Main Fan"
            )
        )

        header.addStretch()

        self.main_fan_state_label = (
            self._create_state_text()
        )

        header.addWidget(
            self.main_fan_state_label
        )

        layout.addLayout(
            header
        )

        # Power
        control_row = QHBoxLayout()

        state_label = QLabel(
            "Power"
        )

        set_label_role(
            state_label,
            "fieldLabel",
        )

        self.main_fan_button = QPushButton(
            "OFF"
        )

        self.main_fan_button.setCheckable(
            True
        )

        set_role(
            self.main_fan_button,
            "toggle",
        )

        control_row.addWidget(
            state_label
        )

        control_row.addStretch()

        control_row.addWidget(
            self.main_fan_button
        )

        layout.addLayout(
            control_row
        )

        # PWM
        pwm_row = QHBoxLayout()

        pwm_label = QLabel(
            "PWM"
        )

        set_label_role(
            pwm_label,
            "fieldLabel",
        )

        self.main_fan_pwm_combo = (
            self._create_pwm_combo()
        )

        self.main_fan_pwm_combo.setMinimumWidth(
            110
        )

        pwm_row.addWidget(
            pwm_label
        )

        pwm_row.addStretch()

        pwm_row.addWidget(
            self.main_fan_pwm_combo
        )

        layout.addLayout(
            pwm_row
        )

        return card

    # =================================================================
    # SMOKE FAN CARD
    # =================================================================

    def _create_smoke_fan_card(
        self,
    ) -> QFrame:
        """Create Smoke Fan card."""

        card = self._new_card()

        layout = QVBoxLayout(
            card
        )

        layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        layout.setSpacing(
            10
        )

        header = QHBoxLayout()

        header.addWidget(
            self._create_card_title(
                "Smoke Fan"
            )
        )

        header.addStretch()

        self.smoke_fan_state_label = (
            self._create_state_text()
        )

        header.addWidget(
            self.smoke_fan_state_label
        )

        layout.addLayout(
            header
        )

        # Power
        control_row = QHBoxLayout()

        state_label = QLabel(
            "Power"
        )

        set_label_role(
            state_label,
            "fieldLabel",
        )

        self.smoke_fan_button = QPushButton(
            "OFF"
        )

        self.smoke_fan_button.setCheckable(
            True
        )

        set_role(
            self.smoke_fan_button,
            "toggle",
        )

        control_row.addWidget(
            state_label
        )

        control_row.addStretch()

        control_row.addWidget(
            self.smoke_fan_button
        )

        layout.addLayout(
            control_row
        )

        # PWM
        pwm_row = QHBoxLayout()

        pwm_label = QLabel(
            "PWM"
        )

        set_label_role(
            pwm_label,
            "fieldLabel",
        )

        self.smoke_fan_pwm_combo = (
            self._create_pwm_combo()
        )

        self.smoke_fan_pwm_combo.setMinimumWidth(
            110
        )

        pwm_row.addWidget(
            pwm_label
        )

        pwm_row.addStretch()

        pwm_row.addWidget(
            self.smoke_fan_pwm_combo
        )

        layout.addLayout(
            pwm_row
        )

        return card

    # =================================================================
    # SMOKE MACHINE CARD
    # =================================================================

    def _create_smoke_machine_card(
        self,
    ) -> QFrame:
        """
        Create Smoke Machine card.

        Manual logging only.
        """

        card = self._new_card()

        layout = QVBoxLayout(
            card
        )

        layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        layout.setSpacing(
            9
        )

        header = QHBoxLayout()

        header.addWidget(
            self._create_card_title(
                "Smoke Machine"
            )
        )

        header.addStretch()

        self.smoke_machine_state_label = (
            self._create_state_text()
        )

        header.addWidget(
            self.smoke_machine_state_label
        )

        layout.addLayout(
            header
        )

        row = QHBoxLayout()

        description = QLabel(
            "Manual log state"
        )

        set_label_role(
            description,
            "fieldLabel",
        )

        self.smoke_machine_button = QPushButton(
            "OFF"
        )

        self.smoke_machine_button.setCheckable(
            True
        )

        set_role(
            self.smoke_machine_button,
            "toggle",
        )

        row.addWidget(
            description
        )

        row.addStretch()

        row.addWidget(
            self.smoke_machine_button
        )

        layout.addLayout(
            row
        )

        note = QLabel(
            "Does not control smoke-machine hardware"
        )

        set_label_role(
            note,
            "muted",
        )

        layout.addWidget(
            note
        )

        return card

    # =================================================================
    # RECORDING / LIVE PLOT CARD
    # =================================================================

    def _create_recording_card(
        self,
    ) -> QFrame:
        """
        Create Recording card including Live Plot control.

        Live Plot is independent of recording.
        """

        card = self._new_card()

        layout = QHBoxLayout(
            card
        )

        layout.setContentsMargins(
            16,
            13,
            16,
            13,
        )

        layout.setSpacing(
            18
        )

        # -------------------------------------------------------------
        # Recording state
        # -------------------------------------------------------------

        text_layout = QVBoxLayout()

        text_layout.setSpacing(
            3
        )

        title = self._create_card_title(
            "Recording"
        )

        self.recording_status_label = QLabel(
            "Not recording"
        )

        set_label_role(
            self.recording_status_label,
            "statusOff",
        )

        text_layout.addWidget(
            title
        )

        text_layout.addWidget(
            self.recording_status_label
        )

        layout.addLayout(
            text_layout
        )

        layout.addStretch()

        # -------------------------------------------------------------
        # Live plot control
        # -------------------------------------------------------------

        plot_layout = QVBoxLayout()

        plot_layout.setSpacing(
            3
        )

        plot_title = QLabel(
            "Live plot"
        )

        set_label_role(
            plot_title,
            "fieldLabel",
        )

        self.live_plot_button = QPushButton(
            "ON"
        )

        self.live_plot_button.setCheckable(
            True
        )

        self.live_plot_button.setChecked(
            True
        )

        self.live_plot_button.setMinimumWidth(
            90
        )

        self.live_plot_button.setToolTip(
            "Controls graph updates only. "
            "Sensors, live values and recording continue."
        )

        set_role(
            self.live_plot_button,
            "toggle",
        )

        plot_layout.addWidget(
            plot_title
        )

        plot_layout.addWidget(
            self.live_plot_button
        )

        layout.addLayout(
            plot_layout
        )

        # -------------------------------------------------------------
        # Recording buttons
        # -------------------------------------------------------------

        self.start_recording_button = QPushButton(
            "Start Recording"
        )

        set_role(
            self.start_recording_button,
            "record",
        )

        self.stop_recording_button = QPushButton(
            "Stop Recording"
        )

        set_role(
            self.stop_recording_button,
            "stopSequence",
        )

        self.start_recording_button.setMinimumWidth(
            130
        )

        self.stop_recording_button.setMinimumWidth(
            130
        )

        layout.addWidget(
            self.start_recording_button
        )

        layout.addWidget(
            self.stop_recording_button
        )

        return card

    # =================================================================
    # CAMERA CARD
    # =================================================================

    def _create_camera_card(
        self,
    ) -> QFrame:
        """Create camera source, toggle, and recording controls."""

        card = self._new_card()

        layout = QVBoxLayout(
            card
        )

        layout.setContentsMargins(
            16,
            13,
            16,
            13,
        )

        layout.setSpacing(
            8,
        )

        title = self._create_card_title(
            "Camera"
        )
        layout.addWidget(title)

        source_row = QHBoxLayout()
        source_row.setContentsMargins(0, 0, 0, 0)
        source_label = QLabel("Camera source")
        set_label_role(source_label, "fieldLabel")
        self.camera_source_combo = QComboBox()
        self.camera_source_combo.setMinimumWidth(170)
        self.camera_source_combo.addItem("Camera 0", 0)
        self.camera_source_combo.setCurrentIndex(0)

        source_row.addWidget(source_label)
        source_row.addWidget(self.camera_source_combo)
        source_row.addStretch()
        layout.addLayout(source_row)

        camera_row = QHBoxLayout()
        camera_row.setContentsMargins(0, 0, 0, 0)
        camera_label = QLabel("Camera")
        set_label_role(camera_label, "fieldLabel")
        self.camera_button = QPushButton("OFF")
        self.camera_button.setCheckable(True)
        self.camera_button.setMinimumWidth(90)
        set_role(self.camera_button, "toggle")
        camera_row.addWidget(camera_label)
        camera_row.addWidget(self.camera_button)
        camera_row.addStretch()
        layout.addLayout(camera_row)

        auto_exposure_row = QHBoxLayout()
        auto_exposure_row.setContentsMargins(0, 0, 0, 0)
        auto_exposure_label = QLabel("Auto exposure")
        set_label_role(auto_exposure_label, "fieldLabel")
        self.auto_exposure_checkbox = QCheckBox()
        self.auto_exposure_checkbox.setChecked(True)
        auto_exposure_row.addWidget(auto_exposure_label)
        auto_exposure_row.addWidget(self.auto_exposure_checkbox)
        auto_exposure_row.addStretch()
        layout.addLayout(auto_exposure_row)

        exposure_row = QHBoxLayout()
        exposure_row.setContentsMargins(0, 0, 0, 0)
        exposure_label = QLabel("Exposure")
        set_label_role(exposure_label, "fieldLabel")
        self.exposure_spin = QSpinBox()
        self.exposure_spin.setRange(-20, 10000)
        self.exposure_spin.setSingleStep(1)
        self.exposure_spin.setEnabled(False)
        exposure_row.addWidget(exposure_label)
        exposure_row.addWidget(self.exposure_spin)
        exposure_row.addStretch()
        layout.addLayout(exposure_row)

        gain_row = QHBoxLayout()
        gain_row.setContentsMargins(0, 0, 0, 0)
        gain_label = QLabel("Gain")
        set_label_role(gain_label, "fieldLabel")
        self.gain_spin = QSpinBox()
        self.gain_spin.setRange(0, 10000)
        self.gain_spin.setSingleStep(1)
        self.gain_spin.setEnabled(False)
        gain_row.addWidget(gain_label)
        gain_row.addWidget(self.gain_spin)
        gain_row.addStretch()
        layout.addLayout(gain_row)

        self.record_video_checkbox = QCheckBox(
            "Record video"
        )
        self.record_video_checkbox.setChecked(False)
        layout.addWidget(self.record_video_checkbox)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_label = QLabel("Status")
        set_label_role(status_label, "fieldLabel")
        self.camera_status_label = QLabel(config.CAMERA_NOT_AVAILABLE_TEXT)
        set_label_role(self.camera_status_label, "statusOff")
        status_row.addWidget(status_label)
        status_row.addWidget(self.camera_status_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        return card

    # =================================================================
    # STOP ALL
    # =================================================================

    def _create_stop_all_button(
        self,
    ) -> QPushButton:
        """Create STOP ALL safety control."""

        button = QPushButton(
            "STOP ALL"
        )

        set_role(
            button,
            "stopAll",
        )

        button.setToolTip(
            "Stops both fans and any running sequence. "
            "Manual recording continues. "
            "Sequence-owned recording is stopped."
        )

        button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        return button

    # =================================================================
    # PWM COMBO
    # =================================================================

    @staticmethod
    def _create_pwm_combo() -> QComboBox:
        """Create PWM selector."""

        combo = QComboBox()

        for pwm in config.PWM_LEVELS:

            combo.addItem(
                f"{pwm} %",
                pwm,
            )

        return combo

    # =================================================================
    # SIGNAL CONNECTIONS
    # =================================================================

    def _connect_internal_signals(
        self,
    ) -> None:
        """Connect widgets to public signals."""

        # Main fan
        self.main_fan_button.toggled.connect(
            self._on_main_fan_toggled
        )

        self.main_fan_pwm_combo.currentIndexChanged.connect(
            self._on_main_fan_pwm_changed
        )

        # Smoke fan
        self.smoke_fan_button.toggled.connect(
            self._on_smoke_fan_toggled
        )

        self.smoke_fan_pwm_combo.currentIndexChanged.connect(
            self._on_smoke_fan_pwm_changed
        )

        # Sensors
        self.sensor_1_button.toggled.connect(
            self._on_sensor_1_toggled
        )

        self.sensor_2_button.toggled.connect(
            self._on_sensor_2_toggled
        )

        # Smoke machine
        self.smoke_machine_button.toggled.connect(
            self._on_smoke_machine_toggled
        )

        # Recording
        self.start_recording_button.clicked.connect(
            self.start_recording_requested.emit
        )

        self.stop_recording_button.clicked.connect(
            self.stop_recording_requested.emit
        )

        # Camera
        self.camera_button.toggled.connect(
            self._on_camera_toggled
        )

        self.camera_source_combo.currentIndexChanged.connect(
            self._on_camera_source_changed
        )

        self.auto_exposure_checkbox.toggled.connect(
            self._on_auto_exposure_toggled
        )

        self.exposure_spin.valueChanged.connect(
            self._on_exposure_changed
        )

        self.gain_spin.valueChanged.connect(
            self._on_gain_changed
        )

        self.record_video_checkbox.toggled.connect(
            self._on_record_video_toggled
        )

        # Live plot
        self.live_plot_button.toggled.connect(
            self._on_live_plot_toggled
        )

        # STOP ALL
        self.stop_all_button.clicked.connect(
            self.stop_all_requested.emit
        )

    # =================================================================
    # MAIN FAN EVENTS
    # =================================================================

    def _on_main_fan_toggled(
        self,
        active: bool,
    ) -> None:

        self._set_toggle_button_text(
            self.main_fan_button,
            active,
        )

        self._set_state_label(
            self.main_fan_state_label,
            active,
        )

        self.main_fan_active_changed.emit(
            active
        )

    def _on_main_fan_pwm_changed(
        self,
    ) -> None:

        pwm = (
            self.main_fan_pwm_combo.currentData()
        )

        if pwm is not None:

            self.main_fan_pwm_changed.emit(
                int(pwm)
            )

    # =================================================================
    # SMOKE FAN EVENTS
    # =================================================================

    def _on_smoke_fan_toggled(
        self,
        active: bool,
    ) -> None:

        self._set_toggle_button_text(
            self.smoke_fan_button,
            active,
        )

        self._set_state_label(
            self.smoke_fan_state_label,
            active,
        )

        self.smoke_fan_active_changed.emit(
            active
        )

    def _on_smoke_fan_pwm_changed(
        self,
    ) -> None:

        pwm = (
            self.smoke_fan_pwm_combo.currentData()
        )

        if pwm is not None:

            self.smoke_fan_pwm_changed.emit(
                int(pwm)
            )

    # =================================================================
    # SENSOR EVENTS
    # =================================================================

    def _on_sensor_1_toggled(
        self,
        active: bool,
    ) -> None:

        self._set_toggle_button_text(
            self.sensor_1_button,
            active,
        )

        self._set_state_label(
            self.sensor_1_state_label,
            active,
        )

        if not active:

            self.set_sensor_1_voltage(
                None
            )

        self.sensor_1_active_changed.emit(
            active
        )

    def _on_sensor_2_toggled(
        self,
        active: bool,
    ) -> None:

        self._set_toggle_button_text(
            self.sensor_2_button,
            active,
        )

        self._set_state_label(
            self.sensor_2_state_label,
            active,
        )

        if not active:

            self.set_sensor_2_voltage(
                None
            )

        self.sensor_2_active_changed.emit(
            active
        )

    # =================================================================
    # SMOKE MACHINE EVENT
    # =================================================================

    def _on_smoke_machine_toggled(
        self,
        active: bool,
    ) -> None:

        self._set_toggle_button_text(
            self.smoke_machine_button,
            active,
        )

        self._set_state_label(
            self.smoke_machine_state_label,
            active,
        )

        self.smoke_machine_active_changed.emit(
            active
        )

    # =================================================================
    # LIVE PLOT EVENT
    # =================================================================

    def _on_camera_toggled(
        self,
        enabled: bool,
    ) -> None:
        """Request the camera to be enabled or disabled."""

        self._camera_enabled = bool(enabled)
        self._set_toggle_button_text(
            self.camera_button,
            self._camera_enabled,
        )
        self.camera_button.setEnabled(True)
        self.camera_enabled_changed.emit(
            self._camera_enabled
        )

    def _on_camera_source_changed(
        self,
        index: int,
    ) -> None:
        """Request the selected camera source to be opened or switched."""

        source_index = self.camera_source_combo.itemData(index)
        if source_index is None:
            return
        self.camera_source_changed.emit(int(source_index))

    def _on_auto_exposure_toggled(
        self,
        enabled: bool,
    ) -> None:
        """Request automatic exposure to be enabled or disabled."""

        self._camera_auto_exposure = bool(enabled)
        self._update_camera_control_state()
        self.auto_exposure_changed.emit(self._camera_auto_exposure)

    def _on_exposure_changed(
        self,
        value: int,
    ) -> None:
        """Request a fixed exposure value."""

        if self.exposure_spin.isEnabled():
            self.exposure_changed.emit(int(value))

    def _on_gain_changed(
        self,
        value: int,
    ) -> None:
        """Request a fixed gain value."""

        if self.gain_spin.isEnabled():
            self.gain_changed.emit(int(value))

    def _on_record_video_toggled(
        self,
        enabled: bool,
    ) -> None:
        """Request video capture to be enabled while recording."""

        self._record_video = bool(enabled)
        self.record_video_changed.emit(
            self._record_video
        )

    def _on_live_plot_toggled(
        self,
        enabled: bool,
    ) -> None:
        """
        Request live graph updates to be enabled or disabled.

        No sensor, logger or hardware state is changed here.
        """

        self._live_plot_enabled = bool(
            enabled
        )

        self._set_toggle_button_text(
            self.live_plot_button,
            self._live_plot_enabled,
        )

        self.live_plot_enabled_changed.emit(
            self._live_plot_enabled
        )

    # =================================================================
    # INITIAL STATE
    # =================================================================

    def _set_initial_state(
        self,
    ) -> None:
        """Apply safe startup state."""

        self.set_main_fan_active(
            config.DEFAULT_MAIN_FAN_ACTIVE
        )

        self.set_smoke_fan_active(
            config.DEFAULT_SMOKE_FAN_ACTIVE
        )

        self.set_main_fan_pwm(
            config.DEFAULT_MAIN_FAN_PWM
        )

        self.set_smoke_fan_pwm(
            config.DEFAULT_SMOKE_FAN_PWM
        )

        self.set_sensor_1_active(
            config.DEFAULT_SENSOR_1_ACTIVE
        )

        self.set_sensor_2_active(
            config.DEFAULT_SENSOR_2_ACTIVE
        )

        self.set_sensor_1_voltage(
            None
        )

        self.set_sensor_2_voltage(
            None
        )

        self.set_smoke_machine_active(
            config.DEFAULT_SMOKE_MACHINE_ACTIVE
        )

        self.set_recording_state(
            False
        )

        self.set_camera_state(
            False,
            config.CAMERA_NOT_AVAILABLE_TEXT,
        )

        self.set_record_video_enabled(
            False
        )

        self.set_live_plot_enabled(
            True
        )

        self.set_sequence_running(
            False
        )

    # =================================================================
    # DISPLAY HELPERS
    # =================================================================

    @staticmethod
    def _set_toggle_button_text(
        button: QPushButton,
        active: bool,
    ) -> None:

        button.setText(
            "ON"
            if active
            else "OFF"
        )

    @staticmethod
    def _set_state_label(
        label: QLabel,
        active: bool,
    ) -> None:
        """Update small ON/OFF state label."""

        label.setText(
            "ON"
            if active
            else "OFF"
        )

        set_label_role(
            label,
            "statusOn"
            if active
            else "statusOff",
        )

    @staticmethod
    def _format_voltage(
        voltage: Optional[float],
    ) -> str:

        if voltage is None:
            return "-- V"

        return f"{float(voltage):.3f} V"

    # =================================================================
    # PUBLIC FAN UPDATE METHODS
    # =================================================================

    def set_main_fan_active(
        self,
        active: bool,
    ) -> None:

        self.main_fan_button.blockSignals(
            True
        )

        self.main_fan_button.setChecked(
            bool(active)
        )

        self._set_toggle_button_text(
            self.main_fan_button,
            active,
        )

        self.main_fan_button.blockSignals(
            False
        )

        self._set_state_label(
            self.main_fan_state_label,
            active,
        )

    def set_smoke_fan_active(
        self,
        active: bool,
    ) -> None:

        self.smoke_fan_button.blockSignals(
            True
        )

        self.smoke_fan_button.setChecked(
            bool(active)
        )

        self._set_toggle_button_text(
            self.smoke_fan_button,
            active,
        )

        self.smoke_fan_button.blockSignals(
            False
        )

        self._set_state_label(
            self.smoke_fan_state_label,
            active,
        )

    def set_main_fan_pwm(
        self,
        pwm_percent: int,
    ) -> None:

        index = (
            self.main_fan_pwm_combo.findData(
                pwm_percent
            )
        )

        if index >= 0:

            self.main_fan_pwm_combo.blockSignals(
                True
            )

            self.main_fan_pwm_combo.setCurrentIndex(
                index
            )

            self.main_fan_pwm_combo.blockSignals(
                False
            )

    def set_smoke_fan_pwm(
        self,
        pwm_percent: int,
    ) -> None:

        index = (
            self.smoke_fan_pwm_combo.findData(
                pwm_percent
            )
        )

        if index >= 0:

            self.smoke_fan_pwm_combo.blockSignals(
                True
            )

            self.smoke_fan_pwm_combo.setCurrentIndex(
                index
            )

            self.smoke_fan_pwm_combo.blockSignals(
                False
            )

    # =================================================================
    # PUBLIC SENSOR UPDATE METHODS
    # =================================================================

    def set_sensor_1_active(
        self,
        active: bool,
    ) -> None:

        self.sensor_1_button.blockSignals(
            True
        )

        self.sensor_1_button.setChecked(
            bool(active)
        )

        self._set_toggle_button_text(
            self.sensor_1_button,
            active,
        )

        self.sensor_1_button.blockSignals(
            False
        )

        self._set_state_label(
            self.sensor_1_state_label,
            active,
        )

        if not active:

            self.set_sensor_1_voltage(
                None
            )

    def set_sensor_2_active(
        self,
        active: bool,
    ) -> None:

        self.sensor_2_button.blockSignals(
            True
        )

        self.sensor_2_button.setChecked(
            bool(active)
        )

        self._set_toggle_button_text(
            self.sensor_2_button,
            active,
        )

        self.sensor_2_button.blockSignals(
            False
        )

        self._set_state_label(
            self.sensor_2_state_label,
            active,
        )

        if not active:

            self.set_sensor_2_voltage(
                None
            )

    # =================================================================
    # PUBLIC SENSOR VOLTAGE DISPLAY
    # =================================================================

    def set_sensor_1_voltage(
        self,
        voltage: Optional[float],
    ) -> None:
        """Update Sensor 1 voltage display."""

        self._sensor_1_voltage = voltage

        self.sensor_1_voltage_label.setText(
            self._format_voltage(
                voltage
            )
        )

    def set_sensor_2_voltage(
        self,
        voltage: Optional[float],
    ) -> None:
        """Update Sensor 2 voltage display."""

        self._sensor_2_voltage = voltage

        self.sensor_2_voltage_label.setText(
            self._format_voltage(
                voltage
            )
        )

    def update_sensor_values(
        self,
        sensor_1_active: bool,
        sensor_1_voltage: Optional[float],
        sensor_2_active: bool,
        sensor_2_voltage: Optional[float],
    ) -> None:
        """Update both sensor cards from one shared sample."""

        self.set_sensor_1_active(
            sensor_1_active
        )

        self.set_sensor_2_active(
            sensor_2_active
        )

        self.set_sensor_1_voltage(
            sensor_1_voltage
            if sensor_1_active
            else None
        )

        self.set_sensor_2_voltage(
            sensor_2_voltage
            if sensor_2_active
            else None
        )

    # =================================================================
    # PUBLIC SMOKE MACHINE UPDATE
    # =================================================================

    def set_smoke_machine_active(
        self,
        active: bool,
    ) -> None:

        self.smoke_machine_button.blockSignals(
            True
        )

        self.smoke_machine_button.setChecked(
            bool(active)
        )

        self._set_toggle_button_text(
            self.smoke_machine_button,
            active,
        )

        self.smoke_machine_button.blockSignals(
            False
        )

        self._set_state_label(
            self.smoke_machine_state_label,
            active,
        )

    # =================================================================
    # LIVE PLOT STATE
    # =================================================================

    def set_live_plot_enabled(
        self,
        enabled: bool,
    ) -> None:
        """
        Synchronize Live Plot button without emitting a signal.

        MainWindow can use this when plotting is automatically frozen
        after a sequence.
        """

        self._live_plot_enabled = bool(
            enabled
        )

        self.live_plot_button.blockSignals(
            True
        )

        self.live_plot_button.setChecked(
            self._live_plot_enabled
        )

        self._set_toggle_button_text(
            self.live_plot_button,
            self._live_plot_enabled,
        )

        self.live_plot_button.blockSignals(
            False
        )

    def get_live_plot_enabled(
        self,
    ) -> bool:
        """Return current Live Plot selection."""

        return self._live_plot_enabled

    def set_camera_state(
        self,
        enabled: bool,
        status_text: str = config.CAMERA_ON_TEXT,
    ) -> None:
        """Synchronize the camera control and status text without emitting a signal."""

        self._camera_enabled = bool(enabled)

        self.camera_button.blockSignals(True)
        self.camera_button.setChecked(self._camera_enabled)
        self._set_toggle_button_text(self.camera_button, self._camera_enabled)
        self.camera_button.blockSignals(False)

        self.camera_status_label.setText(str(status_text).strip() or config.CAMERA_OFF_TEXT)

        if self._camera_enabled:
            set_label_role(self.camera_status_label, "statusOn")
        else:
            set_label_role(self.camera_status_label, "statusOff")

        self.camera_button.setEnabled(True)
        self._update_camera_control_state()

    def set_camera_source_options(
        self,
        available: list[tuple[int, str]],
    ) -> None:
        """Populate the camera-source dropdown in a stable, non-growing way."""

        self.camera_source_combo.blockSignals(True)
        self.camera_source_combo.clear()

        if not available:
            self.camera_source_combo.addItem("Camera 0", 0)
            self.camera_source_combo.setCurrentIndex(0)
            self.camera_source_combo.blockSignals(False)
            return

        for index, label in available:
            self.camera_source_combo.addItem(label, index)

        self.camera_source_combo.blockSignals(False)

    def get_camera_source_index(
        self,
    ) -> int:
        """Return the currently selected camera index."""

        data = self.camera_source_combo.currentData()
        if data is None:
            return 0
        return int(data)

    def get_camera_enabled(
        self,
    ) -> bool:
        """Return whether the camera has been enabled by the user."""

        return self._camera_enabled

    def set_auto_exposure_enabled(
        self,
        enabled: bool,
        supported: bool = True,
    ) -> None:
        """Synchronize the auto-exposure checkbox without emitting a signal."""

        self._camera_auto_exposure_supported = bool(supported)
        self._camera_auto_exposure = bool(enabled)

        self.auto_exposure_checkbox.blockSignals(True)
        self.auto_exposure_checkbox.setChecked(self._camera_auto_exposure)
        self.auto_exposure_checkbox.blockSignals(False)

        self._update_camera_control_state()

    def set_exposure_value(
        self,
        value: Optional[int],
        supported: bool = True,
    ) -> None:
        """Synchronize the exposure spin box, including negative values."""

        self._camera_exposure_supported = bool(supported)

        self.exposure_spin.blockSignals(True)
        if value is None:
            self.exposure_spin.setValue(0)
        else:
            self.exposure_spin.setValue(int(value))
        self.exposure_spin.blockSignals(False)

        self._update_camera_control_state()

    def set_gain_value(
        self,
        value: Optional[int],
        supported: bool = True,
    ) -> None:
        """Synchronize the gain spin box."""

        self._camera_gain_supported = bool(supported)

        self.gain_spin.blockSignals(True)
        if value is None:
            self.gain_spin.setValue(0)
        else:
            self.gain_spin.setValue(int(value))
        self.gain_spin.blockSignals(False)

        self._update_camera_control_state()

    def _update_camera_control_state(self) -> None:
        """Apply camera-control enable/disable rules from explicit state."""

        locked = self._recording or self._sequence_running
        camera_ready = self._camera_enabled and not locked

        self.camera_source_combo.setEnabled(not locked)
        self.camera_button.setEnabled(not locked)

        self.auto_exposure_checkbox.setEnabled(
            camera_ready and self._camera_auto_exposure_supported
        )

        manual_exposure = camera_ready and not self._camera_auto_exposure

        self.exposure_spin.setEnabled(
            manual_exposure and self._camera_exposure_supported
        )
        self.gain_spin.setEnabled(
            manual_exposure and self._camera_gain_supported
        )

    def set_record_video_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Synchronize the Record video checkbox without emitting a signal."""

        self._record_video = bool(enabled)
        self.record_video_checkbox.blockSignals(True)
        self.record_video_checkbox.setChecked(self._record_video)
        self.record_video_checkbox.blockSignals(False)

    def get_record_video_enabled(
        self,
    ) -> bool:
        """Return whether video capture is selected for the current run."""

        return self._record_video

    # =================================================================
    # RECORDING STATE
    # =================================================================

    def set_recording_state(
        self,
        recording: bool,
    ) -> None:
        """Update displayed recording state."""

        self._recording = bool(
            recording
        )

        if self._recording:

            self.recording_status_label.setText(
                "●  RECORDING"
            )

            set_label_role(
                self.recording_status_label,
                "statusRecording",
            )

            set_role(
                self.start_recording_button,
                "recording",
            )

        else:

            self.recording_status_label.setText(
                "Not recording"
            )

            set_label_role(
                self.recording_status_label,
                "statusOff",
            )

            set_role(
                self.start_recording_button,
                "record",
            )

        self._update_control_lock_state()

    # =================================================================
    # SEQUENCE LOCK
    # =================================================================

    def set_sequence_running(
        self,
        running: bool,
    ) -> None:
        """
        Lock conflicting manual controls while sequence runs.

        Locked:
            - Main fan
            - Smoke fan
            - PWM
            - Sensors
            - Manual recording
            - Metadata

        Still available:
            - Live Plot
            - Smoke-machine manual logging
            - STOP ALL
        """

        self._sequence_running = bool(
            running
        )

        self.sequence_lock_label.setVisible(
            self._sequence_running
        )

        self._update_control_lock_state()

    def set_manual_controls_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Compatibility convenience method."""

        self.set_sequence_running(
            not enabled
        )

    def _update_control_lock_state(
        self,
    ) -> None:
        """Apply enabled/disabled states consistently."""

        manual_enabled = (
            not self._sequence_running
        )

        # Metadata
        self.test_name_input.setEnabled(
            manual_enabled
        )

        self.mount_name_input.setEnabled(
            manual_enabled
        )

        self.comment_input.setEnabled(
            manual_enabled
        )

        # Fan controls
        self.main_fan_button.setEnabled(
            manual_enabled
        )

        self.main_fan_pwm_combo.setEnabled(
            manual_enabled
        )

        self.smoke_fan_button.setEnabled(
            manual_enabled
        )

        self.smoke_fan_pwm_combo.setEnabled(
            manual_enabled
        )

        # Sensors
        self.sensor_1_button.setEnabled(
            manual_enabled
        )

        self.sensor_2_button.setEnabled(
            manual_enabled
        )

        # Recording
        if self._sequence_running:

            self.start_recording_button.setEnabled(
                False
            )

            self.stop_recording_button.setEnabled(
                False
            )

        else:

            self.start_recording_button.setEnabled(
                not self._recording
            )

            self.stop_recording_button.setEnabled(
                self._recording
            )

        # Camera controls use explicit capability/state flags so a temporary
        # recording/sequence lock cannot permanently disable them.
        self._update_camera_control_state()

        # -------------------------------------------------------------
        # Always available
        # -------------------------------------------------------------

        # Display-only graph control.
        self.live_plot_button.setEnabled(
            True
        )

        # Manual smoke-machine logging.
        self.smoke_machine_button.setEnabled(
            True
        )

        # Safety control.
        self.stop_all_button.setEnabled(
            True
        )

    # =================================================================
    # METADATA ACCESS
    # =================================================================

    def get_test_metadata(
        self,
    ) -> dict:
        """Return metadata for manual recording."""

        return {
            "test_name":
                self.test_name_input.text().strip(),

            "mount_name":
                self.mount_name_input.text().strip(),

            "comment":
                self.comment_input.toPlainText().strip(),
        }