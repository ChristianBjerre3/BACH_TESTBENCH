"""
gui/control_tab.py

Manual control tab for the airflow/smoke test bench.

CONTROL is intentionally a manual workflow.

The operator can:
    - Enter metadata for a manual test
    - Manually control both fans
    - Manually enable/disable both optical sensors
    - Manually log the smoke-machine state
    - Start/stop manual recording
    - Use STOP ALL

When an automatic sequence is running, conflicting manual controls
are locked. Smoke-machine logging and STOP ALL remain available.

This module only defines GUI behavior and emits Qt signals.
It does not directly access hardware.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
)

import config


class ControlTab(QWidget):
    """Manual test/control interface."""

    # ================================================================
    # SIGNALS
    # ================================================================

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

    # ================================================================
    # INITIALIZATION
    # ================================================================

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._sequence_running = False
        self._recording = False

        self._build_ui()
        self._connect_internal_signals()
        self._set_initial_state()

    # ================================================================
    # BUILD UI
    # ================================================================

    def _build_ui(self) -> None:
        """Create compact manual-control layout."""

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )

        main_layout.setSpacing(6)

        main_layout.addWidget(
            self._create_metadata_group()
        )

        # ------------------------------------------------------------
        # Sequence lock information
        # ------------------------------------------------------------

        self.sequence_lock_label = QLabel(
            "Sequence currently running - manual controls locked."
        )

        self.sequence_lock_label.setStyleSheet(
            """
            QLabel {
                font-weight: bold;
                padding: 5px;
            }
            """
        )

        self.sequence_lock_label.setVisible(
            False
        )

        main_layout.addWidget(
            self.sequence_lock_label
        )

        # ------------------------------------------------------------
        # Manual controls
        # ------------------------------------------------------------

        main_layout.addWidget(
            self._create_fans_group()
        )

        main_layout.addWidget(
            self._create_sensors_group()
        )

        main_layout.addWidget(
            self._create_smoke_machine_group()
        )

        main_layout.addWidget(
            self._create_recording_group()
        )

        # ------------------------------------------------------------
        # STOP ALL
        # ------------------------------------------------------------

        main_layout.addWidget(
            self._create_stop_all_button()
        )

        main_layout.addStretch(1)

    # ================================================================
    # METADATA
    # ================================================================

    def _create_metadata_group(
        self,
    ) -> QGroupBox:
        """Create compact manual-test metadata section."""

        self.metadata_group = QGroupBox(
            "Manual test information"
        )

        layout = QGridLayout(
            self.metadata_group
        )

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(4)

        self.test_name_input = QLineEdit()
        self.mount_name_input = QLineEdit()
        self.comment_input = QTextEdit()

        self.test_name_input.setPlaceholderText(
            "Example: Manual Test 01"
        )

        self.mount_name_input.setPlaceholderText(
            "Example: Mount A"
        )

        self.comment_input.setPlaceholderText(
            "Optional comment"
        )

        self.comment_input.setFixedHeight(
            40
        )

        layout.addWidget(
            QLabel("Test name:"),
            0,
            0,
        )

        layout.addWidget(
            self.test_name_input,
            0,
            1,
        )

        layout.addWidget(
            QLabel("Mount:"),
            1,
            0,
        )

        layout.addWidget(
            self.mount_name_input,
            1,
            1,
        )

        layout.addWidget(
            QLabel("Comment:"),
            2,
            0,
        )

        layout.addWidget(
            self.comment_input,
            2,
            1,
        )

        return self.metadata_group

    # ================================================================
    # FANS
    # ================================================================

    def _create_fans_group(
        self,
    ) -> QGroupBox:
        """Create compact manual fan controls."""

        self.fans_group = QGroupBox(
            "Manual fan control"
        )

        layout = QGridLayout(
            self.fans_group
        )

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(4)

        # ------------------------------------------------------------
        # Main fan
        # ------------------------------------------------------------

        self.main_fan_button = QPushButton(
            "OFF"
        )

        self.main_fan_button.setCheckable(
            True
        )

        self.main_fan_button.setFixedWidth(
            64
        )

        self.main_fan_pwm_combo = (
            self._create_pwm_combo()
        )

        self.main_fan_pwm_combo.setFixedWidth(
            90
        )

        # ------------------------------------------------------------
        # Smoke fan
        # ------------------------------------------------------------

        self.smoke_fan_button = QPushButton(
            "OFF"
        )

        self.smoke_fan_button.setCheckable(
            True
        )

        self.smoke_fan_button.setFixedWidth(
            64
        )

        self.smoke_fan_pwm_combo = (
            self._create_pwm_combo()
        )

        self.smoke_fan_pwm_combo.setFixedWidth(
            90
        )

        # ------------------------------------------------------------
        # Layout
        # ------------------------------------------------------------

        layout.addWidget(
            QLabel("Main fan"),
            0,
            0,
        )

        layout.addWidget(
            self.main_fan_button,
            0,
            1,
        )

        layout.addWidget(
            QLabel("PWM"),
            0,
            2,
        )

        layout.addWidget(
            self.main_fan_pwm_combo,
            0,
            3,
        )

        layout.addWidget(
            QLabel("Smoke fan"),
            1,
            0,
        )

        layout.addWidget(
            self.smoke_fan_button,
            1,
            1,
        )

        layout.addWidget(
            QLabel("PWM"),
            1,
            2,
        )

        layout.addWidget(
            self.smoke_fan_pwm_combo,
            1,
            3,
        )

        layout.setColumnStretch(
            4,
            1,
        )

        return self.fans_group

    # ================================================================
    # SENSORS
    # ================================================================

    def _create_sensors_group(
        self,
    ) -> QGroupBox:
        """Create manual optical-sensor controls."""

        self.sensors_group = QGroupBox(
            "Optical sensors"
        )

        layout = QGridLayout(
            self.sensors_group
        )

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(4)

        self.sensor_1_button = QPushButton(
            "OFF"
        )

        self.sensor_1_button.setCheckable(
            True
        )

        self.sensor_1_button.setFixedWidth(
            64
        )

        self.sensor_2_button = QPushButton(
            "OFF"
        )

        self.sensor_2_button.setCheckable(
            True
        )

        self.sensor_2_button.setFixedWidth(
            64
        )

        layout.addWidget(
            QLabel("Sensor 1"),
            0,
            0,
        )

        layout.addWidget(
            self.sensor_1_button,
            0,
            1,
        )

        layout.addWidget(
            QLabel("Sensor 2"),
            1,
            0,
        )

        layout.addWidget(
            self.sensor_2_button,
            1,
            1,
        )

        layout.setColumnStretch(
            2,
            1,
        )

        return self.sensors_group

    # ================================================================
    # SMOKE MACHINE
    # ================================================================

    def _create_smoke_machine_group(
        self,
    ) -> QGroupBox:
        """
        Create manual smoke-machine logging control.

        This does not control physical hardware.
        """

        self.smoke_machine_group = QGroupBox(
            "Smoke machine"
        )

        layout = QHBoxLayout(
            self.smoke_machine_group
        )

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        self.smoke_machine_button = QPushButton(
            "OFF"
        )

        self.smoke_machine_button.setCheckable(
            True
        )

        self.smoke_machine_button.setFixedWidth(
            64
        )

        info_label = QLabel(
            "Manual logging only"
        )

        layout.addWidget(
            QLabel("Smoke machine")
        )

        layout.addWidget(
            self.smoke_machine_button
        )

        layout.addWidget(
            info_label
        )

        layout.addStretch(1)

        return self.smoke_machine_group

    # ================================================================
    # RECORDING
    # ================================================================

    def _create_recording_group(
        self,
    ) -> QGroupBox:
        """Create manual recording controls."""

        self.recording_group = QGroupBox(
            "Manual recording"
        )

        layout = QHBoxLayout(
            self.recording_group
        )

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        self.start_recording_button = QPushButton(
            "Start Recording"
        )

        self.stop_recording_button = QPushButton(
            "Stop Recording"
        )

        self.recording_status_label = QLabel(
            "Not recording"
        )

        layout.addWidget(
            self.start_recording_button
        )

        layout.addWidget(
            self.stop_recording_button
        )

        layout.addWidget(
            QLabel("Status:")
        )

        layout.addWidget(
            self.recording_status_label
        )

        layout.addStretch(1)

        return self.recording_group

    # ================================================================
    # STOP ALL
    # ================================================================

    def _create_stop_all_button(
        self,
    ) -> QPushButton:
        """Create compact emergency-style STOP ALL control."""

        self.stop_all_button = QPushButton(
            "STOP ALL"
        )

        self.stop_all_button.setMinimumHeight(
            48
        )

        self.stop_all_button.setMaximumHeight(
            55
        )

        self.stop_all_button.setToolTip(
            "Stops both fans and any running sequence. "
            "Manual recording continues. "
            "Sequence-owned recording is stopped."
        )

        self.stop_all_button.setStyleSheet(
            """
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                background-color: #b00020;
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
            }

            QPushButton:hover {
                background-color: #d00030;
            }

            QPushButton:pressed {
                background-color: #800018;
            }
            """
        )

        return self.stop_all_button

    # ================================================================
    # PWM COMBO
    # ================================================================

    @staticmethod
    def _create_pwm_combo(
    ) -> QComboBox:
        """Create PWM selector from config.PWM_LEVELS."""

        combo = QComboBox()

        for pwm in config.PWM_LEVELS:

            combo.addItem(
                f"{pwm} %",
                pwm,
            )

        return combo

    # ================================================================
    # SIGNAL CONNECTIONS
    # ================================================================

    def _connect_internal_signals(
        self,
    ) -> None:
        """Connect widgets to public ControlTab signals."""

        self.main_fan_button.toggled.connect(
            self._on_main_fan_toggled
        )

        self.main_fan_pwm_combo.currentIndexChanged.connect(
            self._on_main_fan_pwm_changed
        )

        self.smoke_fan_button.toggled.connect(
            self._on_smoke_fan_toggled
        )

        self.smoke_fan_pwm_combo.currentIndexChanged.connect(
            self._on_smoke_fan_pwm_changed
        )

        self.sensor_1_button.toggled.connect(
            self._on_sensor_1_toggled
        )

        self.sensor_2_button.toggled.connect(
            self._on_sensor_2_toggled
        )

        self.smoke_machine_button.toggled.connect(
            self._on_smoke_machine_toggled
        )

        self.start_recording_button.clicked.connect(
            self.start_recording_requested.emit
        )

        self.stop_recording_button.clicked.connect(
            self.stop_recording_requested.emit
        )

        self.stop_all_button.clicked.connect(
            self.stop_all_requested.emit
        )

    # ================================================================
    # FAN EVENTS
    # ================================================================

    def _on_main_fan_toggled(
        self,
        active: bool,
    ) -> None:

        self._set_toggle_button_text(
            self.main_fan_button,
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

    def _on_smoke_fan_toggled(
        self,
        active: bool,
    ) -> None:

        self._set_toggle_button_text(
            self.smoke_fan_button,
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

    # ================================================================
    # SENSOR EVENTS
    # ================================================================

    def _on_sensor_1_toggled(
        self,
        active: bool,
    ) -> None:

        self._set_toggle_button_text(
            self.sensor_1_button,
            active,
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

        self.sensor_2_active_changed.emit(
            active
        )

    # ================================================================
    # SMOKE MACHINE EVENT
    # ================================================================

    def _on_smoke_machine_toggled(
        self,
        active: bool,
    ) -> None:

        self._set_toggle_button_text(
            self.smoke_machine_button,
            active,
        )

        self.smoke_machine_active_changed.emit(
            active
        )

    # ================================================================
    # INITIAL STATE
    # ================================================================

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

        self.set_smoke_machine_active(
            config.DEFAULT_SMOKE_MACHINE_ACTIVE
        )

        self.set_recording_state(
            False
        )

        self.set_sequence_running(
            False
        )

    # ================================================================
    # HELPER
    # ================================================================

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

    # ================================================================
    # PUBLIC FAN UPDATE METHODS
    # ================================================================

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

    # ================================================================
    # PUBLIC SENSOR UPDATE METHODS
    # ================================================================

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

    # ================================================================
    # PUBLIC SMOKE MACHINE UPDATE
    # ================================================================

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

    # ================================================================
    # RECORDING STATE
    # ================================================================

    def set_recording_state(
        self,
        recording: bool,
    ) -> None:
        """
        Update displayed recording state.

        Whether the buttons are usable also depends on whether
        a sequence is currently running.
        """

        self._recording = bool(
            recording
        )

        if self._recording:

            self.recording_status_label.setText(
                "Recording"
            )

        else:

            self.recording_status_label.setText(
                "Not recording"
            )

        self._update_control_lock_state()

    # ================================================================
    # SEQUENCE LOCK
    # ================================================================

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
            - Manual recording controls
            - Manual-test metadata

        Still available:
            - Smoke-machine manual log toggle
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
        """
        Convenience interface.

        True  -> sequence is not locking manual controls.
        False -> manual controls are locked.
        """

        self.set_sequence_running(
            not enabled
        )

    def _update_control_lock_state(
        self,
    ) -> None:
        """
        Apply enabled/disabled states consistently.

        This method keeps recording state and sequence lock state
        from overwriting each other incorrectly.
        """

        manual_enabled = (
            not self._sequence_running
        )

        # ------------------------------------------------------------
        # Metadata
        # ------------------------------------------------------------

        self.test_name_input.setEnabled(
            manual_enabled
        )

        self.mount_name_input.setEnabled(
            manual_enabled
        )

        self.comment_input.setEnabled(
            manual_enabled
        )

        # ------------------------------------------------------------
        # Fan controls
        # ------------------------------------------------------------

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

        # ------------------------------------------------------------
        # Sensor controls
        # ------------------------------------------------------------

        self.sensor_1_button.setEnabled(
            manual_enabled
        )

        self.sensor_2_button.setEnabled(
            manual_enabled
        )

        # ------------------------------------------------------------
        # Manual recording controls
        # ------------------------------------------------------------

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

        # ------------------------------------------------------------
        # These remain available during a sequence
        # ------------------------------------------------------------

        self.smoke_machine_button.setEnabled(
            True
        )

        self.stop_all_button.setEnabled(
            True
        )

    # ================================================================
    # METADATA ACCESS
    # ================================================================

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