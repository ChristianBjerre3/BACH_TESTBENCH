"""
gui/control_tab.py

Redesigned manual CONTROL interface for the Airflow Smoke Test Bench.

The visual design follows the approved dark dashboard concept while
preserving the existing application functionality.

CONTROL remains the manual workflow.

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
    - Sensor 1 live voltage display
    - Sensor 2 live voltage display
    - Manual smoke-machine ON/OFF logging
    - Start/stop manual recording
    - STOP ALL

When a sequence is running:
    - Manual fan controls are locked
    - Sensor controls are locked
    - Metadata is locked
    - Manual recording controls are locked

Still available during a sequence:
    - Smoke-machine manual log toggle
    - STOP ALL

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
    QSizePolicy,
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

    stop_all_requested = Signal()

    # =================================================================
    # INITIALIZATION
    # =================================================================

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._sequence_running = False
        self._recording = False

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
        Build the redesigned CONTROL interface.

        Layout concept:

        ┌──────────────────────┬──────────────────────┐
        │ TEST INFORMATION     │ MAIN FAN             │
        ├──────────────────────┼──────────────────────┤
        │ SENSOR 1             │ SMOKE FAN            │
        ├──────────────────────┼──────────────────────┤
        │ SENSOR 2             │ SMOKE MACHINE        │
        ├──────────────────────┴──────────────────────┤
        │ RECORDING                                   │
        ├─────────────────────────────────────────────┤
        │ STOP ALL                                    │
        └─────────────────────────────────────────────┘

        The final main_window redesign will place STOP ALL together
        with the right-side live panel.
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
        # Recording
        # -------------------------------------------------------------

        self.recording_card = (
            self._create_recording_card()
        )

        main_layout.addWidget(
            self.recording_card
        )

        # -------------------------------------------------------------
        # STOP ALL
        #
        # Kept visible until MainWindow is redesigned.
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
        """Create standard card-title label."""

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
        """Create small ON/OFF state label."""

        label = QLabel(
            "ON" if active else "OFF"
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

        # -------------------------------------------------------------
        # Test name
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Mount
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Comment
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Header
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Main row
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Header
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # ON/OFF
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # PWM
        # -------------------------------------------------------------

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

        IMPORTANT:
        This is manual logging only.
        The Raspberry Pi does not physically control the smoke machine.
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
    # RECORDING CARD
    # =================================================================

    def _create_recording_card(
        self,
    ) -> QFrame:
        """Create manual Recording card."""

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
            12
        )

        # -------------------------------------------------------------
        # Title / status
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
        """Create PWM selector from config.PWM_LEVELS."""

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
        """Connect widgets to existing public signals."""

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
        """Update a small card state label."""

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
        """
        Update Sensor 1 voltage display.

        Display-only. Does not read hardware.
        """

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
        """
        Update Sensor 2 voltage display.

        Display-only. Does not read hardware.
        """

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
        """
        Convenience method for MainWindow.

        This allows MainWindow to update both sensor cards from the
        same sensor sample already used for logging/live plots.
        """

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
    # RECORDING STATE
    # =================================================================

    def set_recording_state(
        self,
        recording: bool,
    ) -> None:
        """
        Update displayed recording state.

        Button availability also depends on sequence state.
        """

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
        Lock conflicting manual controls while a sequence runs.

        Locked:
            - Main fan
            - Smoke fan
            - PWM controls
            - Sensor controls
            - Manual recording
            - Manual-test metadata

        Still available:
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

        # -------------------------------------------------------------
        # Metadata
        # -------------------------------------------------------------

        self.test_name_input.setEnabled(
            manual_enabled
        )

        self.mount_name_input.setEnabled(
            manual_enabled
        )

        self.comment_input.setEnabled(
            manual_enabled
        )

        # -------------------------------------------------------------
        # Fan controls
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Sensor controls
        # -------------------------------------------------------------

        self.sensor_1_button.setEnabled(
            manual_enabled
        )

        self.sensor_2_button.setEnabled(
            manual_enabled
        )

        # -------------------------------------------------------------
        # Recording controls
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Always available
        # -------------------------------------------------------------

        self.smoke_machine_button.setEnabled(
            True
        )

        self.stop_all_button.setEnabled(
            True
        )

    # =================================================================
    # METADATA ACCESS
    # =================================================================

    def get_test_metadata(
        self,
    ) -> dict:
        """Return metadata for a manual recording."""

        return {
            "test_name":
                self.test_name_input.text().strip(),

            "mount_name":
                self.mount_name_input.text().strip(),

            "comment":
                self.comment_input.toPlainText().strip(),
        }