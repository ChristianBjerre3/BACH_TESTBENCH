"""
gui/sequence_tab.py

Sequence tab for the airflow/smoke test bench GUI.

This tab represents the automatic test workflow.

The operator can:
    - Enter test metadata
    - Select which optical sensors should be active
    - Choose whether the sequence should be recorded
    - Manually log the smoke-machine state
    - Build a timed fan sequence
    - Run or stop the sequence

This module only defines the GUI and emits Qt signals.

Actual hardware control, recording, sensor control, and sequence
execution are handled by MainWindow and the services layer.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QHeaderView,
    QLineEdit,
    QTextEdit,
    QCheckBox,
)

import config


class SequenceTab(QWidget):
    """
    GUI for configuring and running automatic test sequences.
    """

    # ================================================================
    # SIGNALS
    # ================================================================

    run_sequence_requested = Signal(list)
    stop_sequence_requested = Signal()

    smoke_machine_active_changed = Signal(bool)

    # ================================================================
    # INITIALIZATION
    # ================================================================

    def __init__(self, parent=None) -> None:
        """Initialize the Sequence tab."""

        super().__init__(parent)

        self._build_ui()
        self._connect_signals()

        # Start with one default sequence step.
        self.add_step()

        self.set_sequence_running(False)

    # ================================================================
    # BUILD UI
    # ================================================================

    def _build_ui(self) -> None:
        """
        Build a compact, self-contained automatic-test interface.
        """

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # ------------------------------------------------------------
        # Metadata
        # ------------------------------------------------------------

        main_layout.addWidget(
            self._create_metadata_group()
        )

        # ------------------------------------------------------------
        # Measurement configuration
        # ------------------------------------------------------------

        main_layout.addWidget(
            self._create_measurement_group()
        )

        # ------------------------------------------------------------
        # Sequence table
        # ------------------------------------------------------------

        main_layout.addWidget(
            self._create_sequence_group(),
            stretch=1,
        )

        # ------------------------------------------------------------
        # Sequence editing buttons
        # ------------------------------------------------------------

        edit_layout = QHBoxLayout()
        edit_layout.setSpacing(6)

        self.add_step_button = QPushButton(
            "Add Step"
        )

        self.remove_step_button = QPushButton(
            "Remove Selected"
        )

        self.clear_steps_button = QPushButton(
            "Clear"
        )

        edit_layout.addWidget(
            self.add_step_button
        )

        edit_layout.addWidget(
            self.remove_step_button
        )

        edit_layout.addWidget(
            self.clear_steps_button
        )

        edit_layout.addStretch()

        main_layout.addLayout(edit_layout)

        # ------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------

        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(6)

        summary_layout.addWidget(
            QLabel("Total:")
        )

        self.total_duration_label = QLabel(
            "0.0 s"
        )

        summary_layout.addWidget(
            self.total_duration_label
        )

        summary_layout.addStretch()

        summary_layout.addWidget(
            QLabel("Status:")
        )

        self.sequence_status_label = QLabel(
            "Stopped"
        )

        summary_layout.addWidget(
            self.sequence_status_label
        )

        main_layout.addLayout(
            summary_layout
        )

        # ------------------------------------------------------------
        # Run / stop controls
        # ------------------------------------------------------------

        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)

        self.run_sequence_button = QPushButton(
            "RUN SEQUENCE"
        )

        self.stop_sequence_button = QPushButton(
            "STOP SEQUENCE"
        )

        self.run_sequence_button.setMinimumHeight(
            40
        )

        self.stop_sequence_button.setMinimumHeight(
            40
        )

        control_layout.addWidget(
            self.run_sequence_button
        )

        control_layout.addWidget(
            self.stop_sequence_button
        )

        main_layout.addLayout(
            control_layout
        )

    # ================================================================
    # METADATA
    # ================================================================

    def _create_metadata_group(
        self,
    ) -> QGroupBox:
        """
        Create test metadata inputs for the sequence workflow.
        """

        group = QGroupBox(
            "Sequence test information"
        )

        layout = QGridLayout(group)

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
            "Example: Sequence Test 01"
        )

        self.mount_name_input.setPlaceholderText(
            "Example: Mount A"
        )

        self.comment_input.setPlaceholderText(
            "Optional comment"
        )

        self.comment_input.setFixedHeight(40)

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

        return group

    # ================================================================
    # MEASUREMENT CONFIGURATION
    # ================================================================

    def _create_measurement_group(
        self,
    ) -> QGroupBox:
        """
        Create sensor, recording, and smoke-machine options.
        """

        group = QGroupBox(
            "Measurements"
        )

        layout = QGridLayout(group)

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(4)

        # ------------------------------------------------------------
        # Sensors
        # ------------------------------------------------------------

        self.sensor_1_checkbox = QCheckBox(
            "Sensor 1"
        )

        self.sensor_2_checkbox = QCheckBox(
            "Sensor 2"
        )

        self.sensor_1_checkbox.setChecked(
            config.DEFAULT_SENSOR_1_ACTIVE
        )

        self.sensor_2_checkbox.setChecked(
            config.DEFAULT_SENSOR_2_ACTIVE
        )

        # ------------------------------------------------------------
        # Recording
        # ------------------------------------------------------------

        self.record_sequence_checkbox = QCheckBox(
            "Record sequence"
        )

        self.record_sequence_checkbox.setChecked(
            True
        )

        # ------------------------------------------------------------
        # Smoke machine
        # ------------------------------------------------------------

        self.smoke_machine_button = QPushButton(
            "OFF"
        )

        self.smoke_machine_button.setCheckable(
            True
        )

        self.smoke_machine_button.setFixedWidth(
            70
        )

        self.smoke_machine_note = QLabel(
            "Manual log only"
        )

        # ------------------------------------------------------------
        # Layout
        # ------------------------------------------------------------

        layout.addWidget(
            self.sensor_1_checkbox,
            0,
            0,
        )

        layout.addWidget(
            self.sensor_2_checkbox,
            0,
            1,
        )

        layout.addWidget(
            self.record_sequence_checkbox,
            0,
            2,
        )

        layout.addWidget(
            QLabel("Smoke machine:"),
            1,
            0,
        )

        layout.addWidget(
            self.smoke_machine_button,
            1,
            1,
        )

        layout.addWidget(
            self.smoke_machine_note,
            1,
            2,
        )

        layout.setColumnStretch(
            3,
            1,
        )

        return group

    # ================================================================
    # SEQUENCE TABLE
    # ================================================================

    def _create_sequence_group(
        self,
    ) -> QGroupBox:
        """
        Create the sequence-step table.
        """

        group = QGroupBox(
            "Sequence steps"
        )

        layout = QVBoxLayout(group)

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        self.sequence_table = QTableWidget()

        self.sequence_table.setColumnCount(
            5
        )

        self.sequence_table.setHorizontalHeaderLabels(
            [
                "Duration [s]",
                "Main Fan",
                "Main PWM",
                "Smoke Fan",
                "Smoke PWM",
            ]
        )

        header = (
            self.sequence_table.horizontalHeader()
        )

        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.sequence_table.verticalHeader().setVisible(
            True
        )

        layout.addWidget(
            self.sequence_table
        )

        return group

    # ================================================================
    # SIGNAL CONNECTIONS
    # ================================================================

    def _connect_signals(
        self,
    ) -> None:
        """
        Connect internal GUI signals.
        """

        self.add_step_button.clicked.connect(
            self.add_step
        )

        self.remove_step_button.clicked.connect(
            self.remove_selected_step
        )

        self.clear_steps_button.clicked.connect(
            self.clear_steps
        )

        self.run_sequence_button.clicked.connect(
            self._on_run_sequence
        )

        self.stop_sequence_button.clicked.connect(
            self.stop_sequence_requested.emit
        )

        self.smoke_machine_button.toggled.connect(
            self._on_smoke_machine_toggled
        )

    # ================================================================
    # METADATA ACCESS
    # ================================================================

    def get_test_metadata(
        self,
    ) -> dict:
        """
        Return metadata entered for this sequence test.
        """

        return {
            "test_name":
                self.test_name_input.text().strip(),

            "mount_name":
                self.mount_name_input.text().strip(),

            "comment":
                self.comment_input.toPlainText().strip(),
        }

    # ================================================================
    # MEASUREMENT OPTIONS
    # ================================================================

    def get_sensor_1_selected(
        self,
    ) -> bool:
        """
        Return whether Sensor 1 should be active for the sequence.
        """

        return self.sensor_1_checkbox.isChecked()

    def get_sensor_2_selected(
        self,
    ) -> bool:
        """
        Return whether Sensor 2 should be active for the sequence.
        """

        return self.sensor_2_checkbox.isChecked()

    def get_record_sequence(
        self,
    ) -> bool:
        """
        Return whether the sequence should be recorded.
        """

        return (
            self.record_sequence_checkbox.isChecked()
        )

    # ================================================================
    # SMOKE MACHINE
    # ================================================================

    def _on_smoke_machine_toggled(
        self,
        active: bool,
    ) -> None:
        """
        Update button text and emit manual smoke-machine log state.
        """

        self.smoke_machine_button.setText(
            "ON"
            if active
            else "OFF"
        )

        self.smoke_machine_active_changed.emit(
            active
        )

    def set_smoke_machine_active(
        self,
        active: bool,
    ) -> None:
        """
        Synchronize smoke-machine GUI state without emitting a signal.
        """

        self.smoke_machine_button.blockSignals(
            True
        )

        self.smoke_machine_button.setChecked(
            bool(active)
        )

        self.smoke_machine_button.setText(
            "ON"
            if active
            else "OFF"
        )

        self.smoke_machine_button.blockSignals(
            False
        )

    # ================================================================
    # ADD STEP
    # ================================================================

    def add_step(
        self,
        duration_s: float = 1.0,
        main_fan_active: bool = False,
        main_fan_pwm_percent: int = 0,
        smoke_fan_active: bool = False,
        smoke_fan_pwm_percent: int = 0,
    ) -> None:
        """
        Add one sequence step to the table.
        """

        row = self.sequence_table.rowCount()

        self.sequence_table.insertRow(
            row
        )

        # ------------------------------------------------------------
        # Duration
        # ------------------------------------------------------------

        duration_spin = QDoubleSpinBox()

        duration_spin.setRange(
            config.MIN_SEQUENCE_STEP_DURATION_S,
            3600.0,
        )

        duration_spin.setDecimals(
            1
        )

        duration_spin.setSingleStep(
            0.1
        )

        duration_spin.setValue(
            float(duration_s)
        )

        duration_spin.valueChanged.connect(
            self._update_total_duration
        )

        self.sequence_table.setCellWidget(
            row,
            0,
            duration_spin,
        )

        # ------------------------------------------------------------
        # Main fan state
        # ------------------------------------------------------------

        main_fan_combo = (
            self._create_on_off_combo()
        )

        self._set_combo_bool_value(
            main_fan_combo,
            main_fan_active,
        )

        self.sequence_table.setCellWidget(
            row,
            1,
            main_fan_combo,
        )

        # ------------------------------------------------------------
        # Main fan PWM
        # ------------------------------------------------------------

        main_pwm_combo = (
            self._create_pwm_combo()
        )

        self._set_combo_value(
            main_pwm_combo,
            main_fan_pwm_percent,
        )

        self.sequence_table.setCellWidget(
            row,
            2,
            main_pwm_combo,
        )

        # ------------------------------------------------------------
        # Smoke fan state
        # ------------------------------------------------------------

        smoke_fan_combo = (
            self._create_on_off_combo()
        )

        self._set_combo_bool_value(
            smoke_fan_combo,
            smoke_fan_active,
        )

        self.sequence_table.setCellWidget(
            row,
            3,
            smoke_fan_combo,
        )

        # ------------------------------------------------------------
        # Smoke fan PWM
        # ------------------------------------------------------------

        smoke_pwm_combo = (
            self._create_pwm_combo()
        )

        self._set_combo_value(
            smoke_pwm_combo,
            smoke_fan_pwm_percent,
        )

        self.sequence_table.setCellWidget(
            row,
            4,
            smoke_pwm_combo,
        )

        self._refresh_step_numbers()
        self._update_total_duration()

    # ================================================================
    # REMOVE STEP
    # ================================================================

    def remove_selected_step(
        self,
    ) -> None:
        """
        Remove the selected sequence step.
        """

        row = (
            self.sequence_table.currentRow()
        )

        if row < 0:
            return

        self.sequence_table.removeRow(
            row
        )

        self._refresh_step_numbers()
        self._update_total_duration()

    # ================================================================
    # CLEAR SEQUENCE
    # ================================================================

    def clear_steps(
        self,
    ) -> None:
        """
        Remove all sequence steps.
        """

        self.sequence_table.setRowCount(
            0
        )

        self._update_total_duration()

    # ================================================================
    # RUN SEQUENCE
    # ================================================================

    def _on_run_sequence(
        self,
    ) -> None:
        """
        Gather all sequence steps and request sequence execution.

        MainWindow handles:
            - Metadata
            - Sensor states
            - Recording
            - Sequence execution
        """

        steps = self.get_sequence_data()

        if not steps:
            return

        self.run_sequence_requested.emit(
            steps
        )

    # ================================================================
    # GET SEQUENCE DATA
    # ================================================================

    def get_sequence_data(
        self,
    ) -> list[dict]:
        """
        Return the complete sequence as a list of dictionaries.
        """

        steps = []

        for row in range(
            self.sequence_table.rowCount()
        ):

            duration_widget = (
                self.sequence_table.cellWidget(
                    row,
                    0,
                )
            )

            main_fan_widget = (
                self.sequence_table.cellWidget(
                    row,
                    1,
                )
            )

            main_pwm_widget = (
                self.sequence_table.cellWidget(
                    row,
                    2,
                )
            )

            smoke_fan_widget = (
                self.sequence_table.cellWidget(
                    row,
                    3,
                )
            )

            smoke_pwm_widget = (
                self.sequence_table.cellWidget(
                    row,
                    4,
                )
            )

            step = {
                "duration_s":
                    float(
                        duration_widget.value()
                    ),

                "main_fan_active":
                    bool(
                        main_fan_widget.currentData()
                    ),

                "main_fan_pwm_percent":
                    int(
                        main_pwm_widget.currentData()
                    ),

                "smoke_fan_active":
                    bool(
                        smoke_fan_widget.currentData()
                    ),

                "smoke_fan_pwm_percent":
                    int(
                        smoke_pwm_widget.currentData()
                    ),
            }

            steps.append(
                step
            )

        return steps

    # ================================================================
    # ON / OFF COMBO
    # ================================================================

    @staticmethod
    def _create_on_off_combo(
    ) -> QComboBox:
        """
        Create an ON/OFF combo box.
        """

        combo = QComboBox()

        combo.addItem(
            "OFF",
            False,
        )

        combo.addItem(
            "ON",
            True,
        )

        return combo

    # ================================================================
    # PWM COMBO
    # ================================================================

    @staticmethod
    def _create_pwm_combo(
    ) -> QComboBox:
        """
        Create PWM selection using config.PWM_LEVELS.
        """

        combo = QComboBox()

        for pwm in config.PWM_LEVELS:

            combo.addItem(
                f"{pwm} %",
                pwm,
            )

        return combo

    # ================================================================
    # COMBO HELPERS
    # ================================================================

    @staticmethod
    def _set_combo_value(
        combo: QComboBox,
        value,
    ) -> None:
        """
        Select combo item matching supplied data value.
        """

        index = combo.findData(
            value
        )

        if index >= 0:
            combo.setCurrentIndex(
                index
            )

    @staticmethod
    def _set_combo_bool_value(
        combo: QComboBox,
        value: bool,
    ) -> None:
        """
        Select ON or OFF in a Boolean combo box.
        """

        index = combo.findData(
            bool(value)
        )

        if index >= 0:
            combo.setCurrentIndex(
                index
            )

    # ================================================================
    # STEP NUMBERS
    # ================================================================

    def _refresh_step_numbers(
        self,
    ) -> None:
        """
        Update vertical row headers.
        """

        for row in range(
            self.sequence_table.rowCount()
        ):

            self.sequence_table.setVerticalHeaderItem(
                row,
                QTableWidgetItem(
                    f"Step {row + 1}"
                ),
            )

    # ================================================================
    # TOTAL DURATION
    # ================================================================

    def _update_total_duration(
        self,
    ) -> None:
        """
        Calculate and display total sequence duration.
        """

        total_duration = 0.0

        for row in range(
            self.sequence_table.rowCount()
        ):

            duration_widget = (
                self.sequence_table.cellWidget(
                    row,
                    0,
                )
            )

            if duration_widget is not None:

                total_duration += (
                    duration_widget.value()
                )

        self.total_duration_label.setText(
            f"{total_duration:.1f} s"
        )

    # ================================================================
    # RUNNING STATE
    # ================================================================

    def set_sequence_running(
        self,
        running: bool,
    ) -> None:
        """
        Lock sequence configuration while a sequence is running.

        The smoke-machine button remains available because it is
        manual logging and is not physically controlled by the sequence.
        """

        self.sequence_status_label.setText(
            "Running"
            if running
            else "Stopped"
        )

        # ------------------------------------------------------------
        # Run / stop
        # ------------------------------------------------------------

        self.run_sequence_button.setEnabled(
            not running
        )

        self.stop_sequence_button.setEnabled(
            running
        )

        # ------------------------------------------------------------
        # Sequence editor
        # ------------------------------------------------------------

        self.add_step_button.setEnabled(
            not running
        )

        self.remove_step_button.setEnabled(
            not running
        )

        self.clear_steps_button.setEnabled(
            not running
        )

        self.sequence_table.setEnabled(
            not running
        )

        # ------------------------------------------------------------
        # Test configuration
        # ------------------------------------------------------------

        self.test_name_input.setEnabled(
            not running
        )

        self.mount_name_input.setEnabled(
            not running
        )

        self.comment_input.setEnabled(
            not running
        )

        self.sensor_1_checkbox.setEnabled(
            not running
        )

        self.sensor_2_checkbox.setEnabled(
            not running
        )

        self.record_sequence_checkbox.setEnabled(
            not running
        )

        # Smoke-machine logging intentionally remains enabled.
        self.smoke_machine_button.setEnabled(
            True
        )