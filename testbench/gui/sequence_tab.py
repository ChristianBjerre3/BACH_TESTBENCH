"""
gui/sequence_tab.py

SEQUENCE interface for the Airflow Smoke Test Bench.

SEQUENCE is the automatic test workflow.

Functionality:
    - Test name
    - Mount
    - Comment
    - Sensor 1 selection
    - Sensor 2 selection
    - Record sequence selection
    - Freeze live plot when sequence ends
    - Manual smoke-machine log state
    - Timed fan sequence table
    - Add step
    - Remove selected step
    - Clear steps
    - Total sequence duration
    - Run sequence
    - Stop sequence

Sequence table:
    - Duration
    - Main fan ON/OFF
    - Main fan PWM
    - Smoke fan ON/OFF
    - Smoke fan PWM

IMPORTANT:
"Freeze live plot when sequence ends" only affects graph updates.

It does NOT:
    - Stop sensors
    - Stop live sensor values
    - Change CSV recording
    - Change sequence timing
    - Change fan control

MainWindow will later read this option and handle the plotting state.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
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
    QSpinBox,
    QAbstractSpinBox,
)

import config

from gui.styles import (
    set_card,
    set_role,
    set_label_role,
    PAGE_MARGIN,
    CARD_SPACING,
)


class SequenceTab(QWidget):
    """GUI for configuring and running automatic test sequences."""

    # =================================================================
    # SIGNALS
    # =================================================================

    run_sequence_requested = Signal(list)
    stop_sequence_requested = Signal()

    smoke_machine_active_changed = Signal(bool)

    # =================================================================
    # INITIALIZATION
    # =================================================================

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._sequence_running = False

        self._build_ui()
        self._connect_signals()

        # Start with one default sequence step.
        self.add_step()

        self.set_sequence_running(
            False
        )

    # =================================================================
    # BUILD UI
    # =================================================================

    def _build_ui(self) -> None:
        """Build automatic-test interface."""

        main_layout = QVBoxLayout(
            self
        )

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
        # Metadata
        # -------------------------------------------------------------

        self.metadata_card = (
            self._create_metadata_card()
        )

        main_layout.addWidget(
            self.metadata_card
        )

        # -------------------------------------------------------------
        # Measurement + smoke-machine cards
        # -------------------------------------------------------------

        options_layout = QHBoxLayout()

        options_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        options_layout.setSpacing(
            CARD_SPACING
        )

        self.measurement_card = (
            self._create_measurement_card()
        )

        self.smoke_machine_card = (
            self._create_smoke_machine_card()
        )

        options_layout.addWidget(
            self.measurement_card,
            stretch=2,
        )

        options_layout.addWidget(
            self.smoke_machine_card,
            stretch=1,
        )

        main_layout.addLayout(
            options_layout
        )

        # -------------------------------------------------------------
        # Sequence editor
        # -------------------------------------------------------------

        self.sequence_card = (
            self._create_sequence_card()
        )

        main_layout.addWidget(
            self.sequence_card,
            stretch=1,
        )

        # -------------------------------------------------------------
        # Run / status
        # -------------------------------------------------------------

        self.run_card = (
            self._create_run_card()
        )

        main_layout.addWidget(
            self.run_card
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
    def _card_title(
        text: str,
    ) -> QLabel:
        """Create card title."""

        label = QLabel(
            text.upper()
        )

        set_label_role(
            label,
            "cardTitle",
        )

        return label

    @staticmethod
    def _field_label(
        text: str,
    ) -> QLabel:
        """Create field label."""

        label = QLabel(
            text
        )

        set_label_role(
            label,
            "fieldLabel",
        )

        return label

    # =================================================================
    # METADATA CARD
    # =================================================================

    def _create_metadata_card(
        self,
    ) -> QFrame:
        """Create sequence test information card."""

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
            self._card_title(
                "Sequence Test Information"
            )
        )

        fields = QGridLayout()

        fields.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        fields.setHorizontalSpacing(
            12
        )

        fields.setVerticalSpacing(
            6
        )

        # -------------------------------------------------------------
        # Inputs
        # -------------------------------------------------------------

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

        self.comment_input.setMaximumHeight(
            58
        )

        # -------------------------------------------------------------
        # Layout
        # -------------------------------------------------------------

        fields.addWidget(
            self._field_label(
                "Test name"
            ),
            0,
            0,
        )

        fields.addWidget(
            self.test_name_input,
            1,
            0,
        )

        fields.addWidget(
            self._field_label(
                "Mount"
            ),
            0,
            1,
        )

        fields.addWidget(
            self.mount_name_input,
            1,
            1,
        )

        fields.addWidget(
            self._field_label(
                "Comment"
            ),
            0,
            2,
        )

        fields.addWidget(
            self.comment_input,
            1,
            2,
        )

        fields.setColumnStretch(
            0,
            1,
        )

        fields.setColumnStretch(
            1,
            1,
        )

        fields.setColumnStretch(
            2,
            2,
        )

        layout.addLayout(
            fields
        )

        return card

    # =================================================================
    # MEASUREMENTS CARD
    # =================================================================

    def _create_measurement_card(
        self,
    ) -> QFrame:
        """
        Create sensor, recording and live-plot options.
        """

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
            10
        )

        layout.addWidget(
            self._card_title(
                "Measurements"
            )
        )

        # -------------------------------------------------------------
        # Sensors
        # -------------------------------------------------------------

        sensor_row = QHBoxLayout()

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

        sensor_row.addWidget(
            self.sensor_1_checkbox
        )

        sensor_row.addWidget(
            self.sensor_2_checkbox
        )

        sensor_row.addStretch()

        layout.addLayout(
            sensor_row
        )

        # -------------------------------------------------------------
        # Recording
        # -------------------------------------------------------------

        self.record_sequence_checkbox = QCheckBox(
            "Record sequence"
        )

        self.record_sequence_checkbox.setChecked(
            True
        )

        layout.addWidget(
            self.record_sequence_checkbox
        )

        self.record_video_checkbox = QCheckBox(
            "Record video"
        )

        self.record_video_checkbox.setChecked(
            False
        )

        layout.addWidget(
            self.record_video_checkbox
        )

        # -------------------------------------------------------------
        # Freeze graph after sequence
        # -------------------------------------------------------------

        self.freeze_plot_after_sequence_checkbox = QCheckBox(
            "Freeze live plot when sequence ends"
        )

        # Default ON:
        # A completed experiment remains visible instead of being
        # gradually pushed out of the rolling live graph.
        self.freeze_plot_after_sequence_checkbox.setChecked(
            True
        )

        self.freeze_plot_after_sequence_checkbox.setToolTip(
            "Stops graph updates when the sequence finishes. "
            "Sensors, live values and recording are not affected."
        )

        layout.addWidget(
            self.freeze_plot_after_sequence_checkbox
        )

        # -------------------------------------------------------------
        # Explanation
        # -------------------------------------------------------------

        note = QLabel(
            "Sensors continue measuring even if the live plot is frozen."
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
    # SMOKE MACHINE CARD
    # =================================================================

    def _create_smoke_machine_card(
        self,
    ) -> QFrame:
        """
        Create manual smoke-machine log card.

        Smoke machine is not physically controlled by sequence.
        """

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
            10
        )

        header = QHBoxLayout()

        header.addWidget(
            self._card_title(
                "Smoke Machine"
            )
        )

        header.addStretch()

        self.smoke_machine_state_label = QLabel(
            "OFF"
        )

        set_label_role(
            self.smoke_machine_state_label,
            "statusOff",
        )

        header.addWidget(
            self.smoke_machine_state_label
        )

        layout.addLayout(
            header
        )

        row = QHBoxLayout()

        label = QLabel(
            "Manual log state"
        )

        set_label_role(
            label,
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
            label
        )

        row.addStretch()

        row.addWidget(
            self.smoke_machine_button
        )

        layout.addLayout(
            row
        )

        self.smoke_machine_note = QLabel(
            "Manual logging only"
        )

        set_label_role(
            self.smoke_machine_note,
            "muted",
        )

        layout.addWidget(
            self.smoke_machine_note
        )

        return card

    # =================================================================
    # SEQUENCE CARD
    # =================================================================

    def _create_sequence_card(
        self,
    ) -> QFrame:
        """Create sequence table and editing controls."""

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
            10
        )

        # -------------------------------------------------------------
        # Header
        # -------------------------------------------------------------

        header_layout = QHBoxLayout()

        header_layout.addWidget(
            self._card_title(
                "Sequence Steps"
            )
        )

        header_layout.addStretch()

        self.total_duration_label = QLabel(
            "0.0 s"
        )

        set_label_role(
            self.total_duration_label,
            "timer",
        )

        total_text = QLabel(
            "Total duration"
        )

        set_label_role(
            total_text,
            "fieldLabel",
        )

        header_layout.addWidget(
            total_text
        )

        header_layout.addWidget(
            self.total_duration_label
        )

        layout.addLayout(
            header_layout
        )

        # -------------------------------------------------------------
        # Table
        # -------------------------------------------------------------

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

        self.sequence_table.setAlternatingRowColors(
            True
        )

        self.sequence_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.sequence_table.setMinimumHeight(
            210
        )

        layout.addWidget(
            self.sequence_table,
            stretch=1,
        )

        # -------------------------------------------------------------
        # Edit buttons
        # -------------------------------------------------------------

        edit_layout = QHBoxLayout()

        edit_layout.setSpacing(
            8
        )

        self.add_step_button = QPushButton(
            "+ Add Step"
        )

        set_role(
            self.add_step_button,
            "primary",
        )

        self.remove_step_button = QPushButton(
            "Remove Selected"
        )

        self.clear_steps_button = QPushButton(
            "Clear"
        )

        self.add_stop_step_button = QPushButton(
            "+ Add Stop Step"
        )

        edit_layout.addWidget(
            self.add_step_button
        )

        edit_layout.addWidget(
            self.add_stop_step_button
        )

        edit_layout.addWidget(
            self.remove_step_button
        )

        edit_layout.addWidget(
            self.clear_steps_button
        )

        edit_layout.addStretch()

        layout.addLayout(
            edit_layout
        )

        return card

    # =================================================================
    # RUN CARD
    # =================================================================

    def _create_run_card(
        self,
    ) -> QFrame:
        """Create sequence status and run controls."""

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
        # Status
        # -------------------------------------------------------------

        status_layout = QVBoxLayout()

        status_layout.setSpacing(
            3
        )

        status_layout.addWidget(
            self._card_title(
                "Sequence"
            )
        )

        self.sequence_status_label = QLabel(
            "Stopped"
        )

        set_label_role(
            self.sequence_status_label,
            "statusOff",
        )

        status_layout.addWidget(
            self.sequence_status_label
        )

        layout.addLayout(
            status_layout
        )

        layout.addStretch()

        # -------------------------------------------------------------
        # Run / stop
        # -------------------------------------------------------------

        self.run_sequence_button = QPushButton(
            "RUN SEQUENCE"
        )

        self.stop_sequence_button = QPushButton(
            "STOP SEQUENCE"
        )

        set_role(
            self.run_sequence_button,
            "run",
        )

        set_role(
            self.stop_sequence_button,
            "stopSequence",
        )

        self.run_sequence_button.setMinimumWidth(
            170
        )

        self.stop_sequence_button.setMinimumWidth(
            150
        )

        layout.addWidget(
            self.run_sequence_button
        )

        layout.addWidget(
            self.stop_sequence_button
        )

        return card

    # =================================================================
    # SIGNAL CONNECTIONS
    # =================================================================

    def _connect_signals(
        self,
    ) -> None:
        """Connect internal GUI signals."""

        self.add_step_button.clicked.connect(
            self.add_step
        )

        self.add_stop_step_button.clicked.connect(
            self.add_stop_step
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

    # =================================================================
    # METADATA ACCESS
    # =================================================================

    def get_test_metadata(
        self,
    ) -> dict:
        """Return metadata entered for sequence test."""

        return {
            "test_name":
                self.test_name_input.text().strip(),

            "mount_name":
                self.mount_name_input.text().strip(),

            "comment":
                self.comment_input.toPlainText().strip(),
        }

    # =================================================================
    # MEASUREMENT OPTIONS
    # =================================================================

    def get_sensor_1_selected(
        self,
    ) -> bool:
        """Return whether Sensor 1 should be active."""

        return (
            self.sensor_1_checkbox.isChecked()
        )

    def get_sensor_2_selected(
        self,
    ) -> bool:
        """Return whether Sensor 2 should be active."""

        return (
            self.sensor_2_checkbox.isChecked()
        )

    def get_record_sequence(
        self,
    ) -> bool:
        """Return whether sequence should be recorded."""

        return (
            self.record_sequence_checkbox.isChecked()
        )

    def get_record_video(
        self,
    ) -> bool:
        """Return whether the sequence should also capture video."""

        return (
            self.record_video_checkbox.isChecked()
        )

    def get_freeze_plot_after_sequence(
        self,
    ) -> bool:
        """
        Return whether live plotting should freeze when the sequence ends.

        This option affects graph updates only.
        """

        return (
            self.freeze_plot_after_sequence_checkbox.isChecked()
        )

    # =================================================================
    # SMOKE MACHINE
    # =================================================================

    def _on_smoke_machine_toggled(
        self,
        active: bool,
    ) -> None:
        """Update display and emit manual log state."""

        self._set_smoke_machine_display(
            active
        )

        self.smoke_machine_active_changed.emit(
            active
        )

    def set_smoke_machine_active(
        self,
        active: bool,
    ) -> None:
        """Synchronize smoke-machine GUI without emitting signal."""

        self.smoke_machine_button.blockSignals(
            True
        )

        self.smoke_machine_button.setChecked(
            bool(active)
        )

        self._set_smoke_machine_display(
            active
        )

        self.smoke_machine_button.blockSignals(
            False
        )

    def _set_smoke_machine_display(
        self,
        active: bool,
    ) -> None:

        self.smoke_machine_button.setText(
            "ON"
            if active
            else "OFF"
        )

        self.smoke_machine_state_label.setText(
            "ON"
            if active
            else "OFF"
        )

        set_label_role(
            self.smoke_machine_state_label,
            "statusOn"
            if active
            else "statusOff",
        )

    # =================================================================
    # ADD STEP
    # =================================================================

    def add_step(
        self,
        duration_s: float | None = None,
        main_fan_active: bool = False,
        main_fan_pwm_percent: int = 0,
        smoke_fan_active: bool = False,
        smoke_fan_pwm_percent: int = 0,
    ) -> None:
        """Add one sequence step, copying the previous step by default."""

        row = self.sequence_table.rowCount()

        if duration_s is None:
            duration_s = 5.0

        if row > 0:
            previous = self._read_step_from_row(row - 1)
            main_fan_active = bool(previous["main_fan_active"])
            main_fan_pwm_percent = int(previous["main_fan_pwm_percent"])
            smoke_fan_active = bool(previous["smoke_fan_active"])
            smoke_fan_pwm_percent = int(previous["smoke_fan_pwm_percent"])
            duration_s = float(previous["duration_s"]) if duration_s is None else float(duration_s)
            if duration_s <= 0:
                duration_s = 5.0

        self.sequence_table.insertRow(row)

        duration_spin = QDoubleSpinBox()
        duration_spin.setRange(config.MIN_SEQUENCE_STEP_DURATION_S, 3600.0)
        duration_spin.setDecimals(1)
        duration_spin.setSingleStep(0.1)
        duration_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        duration_spin.setValue(float(duration_s))
        duration_spin.valueChanged.connect(self._update_total_duration)
        self.sequence_table.setCellWidget(row, 0, duration_spin)

        main_fan_combo = self._create_on_off_combo()
        self._set_combo_bool_value(main_fan_combo, main_fan_active)
        self.sequence_table.setCellWidget(row, 1, main_fan_combo)

        main_pwm_spin = self._create_pwm_spinbox()
        main_pwm_spin.setValue(int(main_fan_pwm_percent))
        self.sequence_table.setCellWidget(row, 2, main_pwm_spin)

        smoke_fan_combo = self._create_on_off_combo()
        self._set_combo_bool_value(smoke_fan_combo, smoke_fan_active)
        self.sequence_table.setCellWidget(row, 3, smoke_fan_combo)

        smoke_pwm_spin = self._create_pwm_spinbox()
        smoke_pwm_spin.setValue(int(smoke_fan_pwm_percent))
        self.sequence_table.setCellWidget(row, 4, smoke_pwm_spin)

        self._refresh_step_numbers()
        self._update_total_duration()

    def add_stop_step(
        self,
    ) -> None:
        """Add a one-second fully-off stop step."""

        row = self.sequence_table.rowCount()

        self.sequence_table.insertRow(row)

        duration_spin = QDoubleSpinBox()
        duration_spin.setRange(config.MIN_SEQUENCE_STEP_DURATION_S, 3600.0)
        duration_spin.setDecimals(1)
        duration_spin.setSingleStep(0.1)
        duration_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        duration_spin.setValue(1.0)
        duration_spin.valueChanged.connect(self._update_total_duration)
        self.sequence_table.setCellWidget(row, 0, duration_spin)

        main_fan_combo = self._create_on_off_combo()
        self._set_combo_bool_value(main_fan_combo, False)
        self.sequence_table.setCellWidget(row, 1, main_fan_combo)

        main_pwm_spin = self._create_stop_pwm_spinbox()
        main_pwm_spin.setValue(0)
        self.sequence_table.setCellWidget(row, 2, main_pwm_spin)

        smoke_fan_combo = self._create_on_off_combo()
        self._set_combo_bool_value(smoke_fan_combo, False)
        self.sequence_table.setCellWidget(row, 3, smoke_fan_combo)

        smoke_pwm_spin = self._create_stop_pwm_spinbox()
        smoke_pwm_spin.setValue(0)
        self.sequence_table.setCellWidget(row, 4, smoke_pwm_spin)

        self._refresh_step_numbers()
        self._update_total_duration()

    # =================================================================
    # REMOVE STEP
    # =================================================================

    def remove_selected_step(
        self,
    ) -> None:
        """Remove selected sequence step."""

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

    # =================================================================
    # CLEAR
    # =================================================================

    def clear_steps(
        self,
    ) -> None:
        """Remove all sequence steps."""

        self.sequence_table.setRowCount(
            0
        )

        self._update_total_duration()

    # =================================================================
    # RUN
    # =================================================================

    def _on_run_sequence(
        self,
    ) -> None:
        """Gather sequence and request execution."""

        steps = (
            self.get_sequence_data()
        )

        if not steps:
            return

        self.run_sequence_requested.emit(
            steps
        )

    # =================================================================
    # GET SEQUENCE DATA
    # =================================================================

    def get_sequence_data(
        self,
    ) -> list[dict]:
        """Return complete sequence."""

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
                        main_pwm_widget.value()
                    ),

                "smoke_fan_active":
                    bool(
                        smoke_fan_widget.currentData()
                    ),

                "smoke_fan_pwm_percent":
                    int(
                        smoke_pwm_widget.value()
                    ),
            }

            steps.append(
                step
            )

        return steps

    # =================================================================
    # COMBO CREATION
    # =================================================================

    @staticmethod
    def _create_on_off_combo(
    ) -> QComboBox:
        """Create ON/OFF combo."""

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

    @staticmethod
    def _create_pwm_spinbox() -> QSpinBox:
        """Create PWM numeric selector from 5 to 100%."""

        spin = QSpinBox()
        spin.setRange(5, 100)
        spin.setSingleStep(1)
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        return spin

    @staticmethod
    def _create_stop_pwm_spinbox() -> QSpinBox:
        """Create a zero-aware stop-step PWM input. The stop step is always 0%."""

        spin = QSpinBox()
        spin.setRange(0, 100)
        spin.setSingleStep(1)
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        return spin

    @staticmethod
    def _create_pwm_combo() -> QComboBox:
        """Backward-compatible alias kept for older references."""

        return SequenceTab._create_pwm_spinbox()
    # =================================================================
    # COMBO HELPERS
    # =================================================================

    @staticmethod
    def _set_combo_value(
        combo: QComboBox,
        value,
    ) -> None:

        index = (
            combo.findData(
                value
            )
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

        index = (
            combo.findData(
                bool(value)
            )
        )

        if index >= 0:

            combo.setCurrentIndex(
                index
            )

    # =================================================================
    # STEP NUMBERS
    # =================================================================

    def _read_step_from_row(
        self,
        row: int,
    ) -> dict:
        """Return the current values from a given step row."""

        duration_widget = self.sequence_table.cellWidget(row, 0)
        main_fan_widget = self.sequence_table.cellWidget(row, 1)
        main_pwm_widget = self.sequence_table.cellWidget(row, 2)
        smoke_fan_widget = self.sequence_table.cellWidget(row, 3)
        smoke_pwm_widget = self.sequence_table.cellWidget(row, 4)

        return {
            "duration_s": float(duration_widget.value()) if duration_widget is not None else 5.0,
            "main_fan_active": bool(main_fan_widget.currentData()) if main_fan_widget is not None else False,
            "main_fan_pwm_percent": int(main_pwm_widget.value()) if main_pwm_widget is not None else 0,
            "smoke_fan_active": bool(smoke_fan_widget.currentData()) if smoke_fan_widget is not None else False,
            "smoke_fan_pwm_percent": int(smoke_pwm_widget.value()) if smoke_pwm_widget is not None else 0,
        }

    def _refresh_step_numbers(
        self,
    ) -> None:
        """Update table row numbers."""

        for row in range(
            self.sequence_table.rowCount()
        ):

            self.sequence_table.setVerticalHeaderItem(
                row,
                QTableWidgetItem(
                    f"Step {row + 1}"
                ),
            )

    # =================================================================
    # TOTAL DURATION
    # =================================================================

    def _update_total_duration(
        self,
    ) -> None:
        """Calculate total sequence duration."""

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

    # =================================================================
    # RUNNING STATE
    # =================================================================

    def set_sequence_running(
        self,
        running: bool,
    ) -> None:
        """
        Lock sequence configuration while running.

        Smoke-machine manual logging remains available.

        Freeze-after-sequence selection is locked while running because
        MainWindow reads it as part of the sequence configuration.
        """

        self._sequence_running = bool(
            running
        )

        # -------------------------------------------------------------
        # Status
        # -------------------------------------------------------------

        self.sequence_status_label.setText(
            "● RUNNING"
            if running
            else "Stopped"
        )

        set_label_role(
            self.sequence_status_label,
            "statusOn"
            if running
            else "statusOff",
        )

        # -------------------------------------------------------------
        # Run / stop
        # -------------------------------------------------------------

        self.run_sequence_button.setEnabled(
            not running
        )

        self.stop_sequence_button.setEnabled(
            running
        )

        # -------------------------------------------------------------
        # Sequence editor
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Test configuration
        # -------------------------------------------------------------

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

        self.freeze_plot_after_sequence_checkbox.setEnabled(
            not running
        )

        # -------------------------------------------------------------
        # Manual smoke-machine logging remains enabled
        # -------------------------------------------------------------

        self.smoke_machine_button.setEnabled(
            True
        )