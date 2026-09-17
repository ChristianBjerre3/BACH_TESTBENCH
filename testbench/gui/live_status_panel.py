"""
gui/live_status_panel.py

Compact live status panel used beside CONTROL and SEQUENCE.

The panel is display-only.

It displays:
    - Sensor 1 state and voltage
    - Sensor 2 state and voltage
    - Main fan state, commanded PWM, and measured RPM
    - Smoke fan state, commanded PWM, and measured RPM
    - Smoke-machine manually logged state
    - Recording state and elapsed recording time
    - Sequence state and current step
    - Live plot state
    - Compact combined Sensor 1 / Sensor 2 live plot

It does NOT:
    - Read the ADC
    - Control hardware
    - Control fans
    - Control sensors
    - Start or stop recording
    - Run sequences
    - Decide whether plotting is enabled

MainWindow pushes all live data into this widget.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QLabel,
    QSizePolicy,
)

import config

from gui.styles import (
    set_card,
    set_label_role,
    CARD_SPACING,
    PLOT_BACKGROUND,
    PLOT_FOREGROUND,
    PLOT_GRID_ALPHA,
    SENSOR_1_COLOR,
    SENSOR_2_COLOR,
    PLOT_LINE_WIDTH,
)


class LiveStatusPanel(QWidget):
    """
    Compact live-data side panel.

    One instance is used beside CONTROL.
    Another is used beside SEQUENCE.

    Both receive the same state from MainWindow.
    """

    # =================================================================
    # INITIALIZATION
    # =================================================================

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        max_points = max(
            1,
            int(
                config.LIVE_PLOT_TIME_WINDOW_S
                * config.SENSOR_SAMPLE_RATE_HZ
            ),
        )

        self._time_data = deque(
            maxlen=max_points
        )

        self._sensor_1_data = deque(
            maxlen=max_points
        )

        self._sensor_2_data = deque(
            maxlen=max_points
        )

        self.setMinimumWidth(
            290
        )

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self._build_ui()

    # =================================================================
    # BUILD UI
    # =================================================================

    def _build_ui(self) -> None:
        """Build compact live-status panel."""

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(
            CARD_SPACING
        )

        # -------------------------------------------------------------
        # Live status card
        # -------------------------------------------------------------

        self.status_card = (
            self._create_status_card()
        )

        layout.addWidget(
            self.status_card
        )

        # -------------------------------------------------------------
        # Live plot card
        # -------------------------------------------------------------

        self.plot_card = (
            self._create_plot_card()
        )

        layout.addWidget(
            self.plot_card,
            stretch=1,
        )

    # =================================================================
    # GENERIC HELPERS
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

    @staticmethod
    def _set_state_label(
        label: QLabel,
        active: bool,
        on_text: str = "ON",
        off_text: str = "OFF",
    ) -> None:
        """Set state text and visual style."""

        label.setText(
            on_text
            if active
            else off_text
        )

        set_label_role(
            label,
            "statusOn"
            if active
            else "statusOff",
        )

    # =================================================================
    # STATUS CARD
    # =================================================================

    def _create_status_card(
        self,
    ) -> QFrame:
        """Create main live-status card."""

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
            11
        )

        # -------------------------------------------------------------
        # Header
        # -------------------------------------------------------------

        header = QHBoxLayout()

        header.addWidget(
            self._card_title(
                "Live Status"
            )
        )

        header.addStretch()

        self.system_ready_label = QLabel(
            "● LIVE"
        )

        set_label_role(
            self.system_ready_label,
            "statusReady",
        )

        header.addWidget(
            self.system_ready_label
        )

        layout.addLayout(
            header
        )

        # -------------------------------------------------------------
        # Sensors
        # -------------------------------------------------------------

        sensor_title = QLabel(
            "SENSORS"
        )

        set_label_role(
            sensor_title,
            "muted",
        )

        layout.addWidget(
            sensor_title
        )

        sensor_grid = QGridLayout()

        sensor_grid.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        sensor_grid.setHorizontalSpacing(
            8
        )

        sensor_grid.setVerticalSpacing(
            7
        )

        self.sensor_1_state_label = QLabel(
            "OFF"
        )

        self.sensor_1_voltage_label = QLabel(
            "-- V"
        )

        self.sensor_1_voltage_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        set_label_role(
            self.sensor_1_voltage_label,
            "liveValueSensor1",
        )

        self.sensor_2_state_label = QLabel(
            "OFF"
        )

        self.sensor_2_voltage_label = QLabel(
            "-- V"
        )

        self.sensor_2_voltage_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        set_label_role(
            self.sensor_2_voltage_label,
            "liveValueSensor2",
        )

        sensor_grid.addWidget(
            self._field_label(
                "Sensor 1"
            ),
            0,
            0,
        )

        sensor_grid.addWidget(
            self.sensor_1_state_label,
            0,
            1,
        )

        sensor_grid.addWidget(
            self.sensor_1_voltage_label,
            0,
            2,
        )

        sensor_grid.addWidget(
            self._field_label(
                "Sensor 2"
            ),
            1,
            0,
        )

        sensor_grid.addWidget(
            self.sensor_2_state_label,
            1,
            1,
        )

        sensor_grid.addWidget(
            self.sensor_2_voltage_label,
            1,
            2,
        )

        sensor_grid.setColumnStretch(
            0,
            1,
        )

        sensor_grid.setColumnStretch(
            2,
            1,
        )

        layout.addLayout(
            sensor_grid
        )

        # -------------------------------------------------------------
        # Divider
        # -------------------------------------------------------------

        layout.addWidget(
            self._create_divider()
        )

        # -------------------------------------------------------------
        # System
        # -------------------------------------------------------------

        system_title = QLabel(
            "SYSTEM"
        )

        set_label_role(
            system_title,
            "muted",
        )

        layout.addWidget(
            system_title
        )

        system_grid = QGridLayout()

        system_grid.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        system_grid.setHorizontalSpacing(
            8
        )

        system_grid.setVerticalSpacing(
            7
        )

        # Fan states
        self.main_fan_state_label = QLabel(
            "OFF"
        )

        self.main_fan_pwm_label = QLabel(
            "0 %"
        )

        self.main_fan_pwm_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        self.main_fan_rpm_label = QLabel("-- RPM")
        self.main_fan_rpm_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        self.smoke_fan_state_label = QLabel(
            "OFF"
        )

        self.smoke_fan_pwm_label = QLabel(
            "0 %"
        )

        self.smoke_fan_pwm_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        self.smoke_fan_rpm_label = QLabel("-- RPM")
        self.smoke_fan_rpm_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        # Smoke machine
        self.smoke_machine_state_label = QLabel(
            "OFF"
        )

        # Recording
        self.recording_state_label = QLabel(
            "Not recording"
        )

        self.elapsed_time_label = QLabel(
            "0.0 s"
        )

        self.elapsed_time_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        # Sequence
        self.sequence_state_label = QLabel(
            "Stopped"
        )

        self.sequence_step_label = QLabel(
            "-"
        )

        self.sequence_step_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        # -------------------------------------------------------------
        # NEW: Live plot state
        # -------------------------------------------------------------

        self.live_plot_state_label = QLabel(
            "ON"
        )

        set_label_role(
            self.live_plot_state_label,
            "statusOn",
        )

        # -------------------------------------------------------------
        # Rows
        # -------------------------------------------------------------

        row = 0

        row = self._add_status_row(
            system_grid,
            row,
            "Main fan",
            self.main_fan_state_label,
            self.main_fan_pwm_label,
        )

        row = self._add_status_row(
            system_grid,
            row,
            "  Measured RPM",
            self._field_label("FG feedback"),
            self.main_fan_rpm_label,
        )

        row = self._add_status_row(
            system_grid,
            row,
            "Smoke fan",
            self.smoke_fan_state_label,
            self.smoke_fan_pwm_label,
        )

        row = self._add_status_row(
            system_grid,
            row,
            "  Measured RPM",
            self._field_label("FG feedback"),
            self.smoke_fan_rpm_label,
        )

        row = self._add_status_row(
            system_grid,
            row,
            "Smoke machine",
            self.smoke_machine_state_label,
            None,
        )

        row = self._add_status_row(
            system_grid,
            row,
            "Recording",
            self.recording_state_label,
            self.elapsed_time_label,
        )

        row = self._add_status_row(
            system_grid,
            row,
            "Sequence",
            self.sequence_state_label,
            self.sequence_step_label,
        )

        self._add_status_row(
            system_grid,
            row,
            "Live plot",
            self.live_plot_state_label,
            None,
        )

        system_grid.setColumnStretch(
            0,
            1,
        )

        system_grid.setColumnStretch(
            1,
            1,
        )

        system_grid.setColumnStretch(
            2,
            1,
        )

        layout.addLayout(
            system_grid
        )

        return card

    # =================================================================
    # STATUS HELPERS
    # =================================================================

    @staticmethod
    def _create_divider() -> QFrame:
        """Create subtle horizontal divider."""

        divider = QFrame()

        divider.setFrameShape(
            QFrame.Shape.HLine
        )

        divider.setFrameShadow(
            QFrame.Shadow.Plain
        )

        divider.setStyleSheet(
            """
            QFrame {
                color: #243A4D;
                background-color: #243A4D;
                max-height: 1px;
                border: none;
            }
            """
        )

        return divider

    @staticmethod
    def _add_status_row(
        grid: QGridLayout,
        row: int,
        title: str,
        value_a: QLabel,
        value_b: Optional[QLabel],
    ) -> int:
        """Add one status row."""

        title_label = QLabel(
            title
        )

        set_label_role(
            title_label,
            "fieldLabel",
        )

        grid.addWidget(
            title_label,
            row,
            0,
        )

        grid.addWidget(
            value_a,
            row,
            1,
        )

        if value_b is not None:

            grid.addWidget(
                value_b,
                row,
                2,
            )

        return row + 1

    # =================================================================
    # LIVE DATA / MINI PLOT CARD
    # =================================================================

    def _create_plot_card(
        self,
    ) -> QFrame:
        """Create combined Sensor 1 / Sensor 2 mini graph."""

        card = self._new_card()

        layout = QVBoxLayout(
            card
        )

        layout.setContentsMargins(
            14,
            14,
            14,
            14,
        )

        layout.setSpacing(
            8
        )

        # -------------------------------------------------------------
        # Header
        # -------------------------------------------------------------

        header = QHBoxLayout()

        header.addWidget(
            self._card_title(
                "Live Data"
            )
        )

        header.addStretch()

        self.plot_window_label = QLabel(
            f"Last {config.LIVE_PLOT_TIME_WINDOW_S} s"
        )

        set_label_role(
            self.plot_window_label,
            "muted",
        )

        header.addWidget(
            self.plot_window_label
        )

        layout.addLayout(
            header
        )

        # -------------------------------------------------------------
        # Plot
        # -------------------------------------------------------------

        self.plot = pg.PlotWidget()

        self.plot.setBackground(
            PLOT_BACKGROUND
        )

        self.plot.setLabel(
            "left",
            "Voltage",
            units="V",
        )

        self.plot.setLabel(
            "bottom",
            "Time",
            units="s",
        )

        self.plot.showGrid(
            x=True,
            y=True,
            alpha=PLOT_GRID_ALPHA,
        )

        self.plot.setMinimumHeight(
            190
        )

        self.plot.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        # -------------------------------------------------------------
        # Axes
        # -------------------------------------------------------------

        for axis_name in (
            "left",
            "bottom",
        ):

            axis = self.plot.getAxis(
                axis_name
            )

            axis.setTextPen(
                pg.mkPen(
                    PLOT_FOREGROUND
                )
            )

            axis.setPen(
                pg.mkPen(
                    PLOT_FOREGROUND
                )
            )

        # -------------------------------------------------------------
        # Legend
        # -------------------------------------------------------------

        legend = self.plot.addLegend(
            offset=(8, 8)
        )

        legend.setLabelTextColor(
            PLOT_FOREGROUND
        )

        # -------------------------------------------------------------
        # Curves
        # -------------------------------------------------------------

        self.sensor_1_curve = self.plot.plot(
            pen=pg.mkPen(
                SENSOR_1_COLOR,
                width=PLOT_LINE_WIDTH,
            ),
            name="Sensor 1",
            connect="finite",
        )

        self.sensor_2_curve = self.plot.plot(
            pen=pg.mkPen(
                SENSOR_2_COLOR,
                width=PLOT_LINE_WIDTH,
            ),
            name="Sensor 2",
            connect="finite",
        )

        layout.addWidget(
            self.plot
        )

        return card

    # =================================================================
    # PUBLIC SENSOR UPDATE
    # =================================================================

    def update_sensor_values(
        self,
        sensor_1_active: bool,
        sensor_1_voltage: Optional[float],
        sensor_2_active: bool,
        sensor_2_voltage: Optional[float],
    ) -> None:
        """Update sensor states and voltage labels."""

        self._set_state_label(
            self.sensor_1_state_label,
            sensor_1_active,
        )

        self._set_state_label(
            self.sensor_2_state_label,
            sensor_2_active,
        )

        self.sensor_1_voltage_label.setText(
            self._format_voltage(
                sensor_1_voltage
                if sensor_1_active
                else None
            )
        )

        self.sensor_2_voltage_label.setText(
            self._format_voltage(
                sensor_2_voltage
                if sensor_2_active
                else None
            )
        )

    # =================================================================
    # PUBLIC FAN UPDATE
    # =================================================================

    def update_fan_status(
        self,
        main_fan_active: bool,
        main_fan_pwm_percent: int,
        smoke_fan_active: bool,
        smoke_fan_pwm_percent: int,
        main_fan_rpm: Optional[float] = None,
        smoke_fan_rpm: Optional[float] = None,
    ) -> None:
        """Update commanded fan states and independent measured FG RPM."""

        self._set_state_label(
            self.main_fan_state_label,
            main_fan_active,
        )

        self.main_fan_pwm_label.setText(
            f"{int(main_fan_pwm_percent)} %"
        )

        self._set_state_label(
            self.smoke_fan_state_label,
            smoke_fan_active,
        )

        self.smoke_fan_pwm_label.setText(
            f"{int(smoke_fan_pwm_percent)} %"
        )

        self.main_fan_rpm_label.setText(
            self._format_rpm(main_fan_rpm)
        )
        self.smoke_fan_rpm_label.setText(
            self._format_rpm(smoke_fan_rpm)
        )

    @staticmethod
    def _format_rpm(rpm: Optional[float]) -> str:
        """Display unavailable measurements differently from measured zero."""
        if rpm is None:
            return "-- RPM"
        return f"{float(rpm):,.0f} RPM".replace(",", " ")

    # =================================================================
    # PUBLIC EXPERIMENT STATUS UPDATE
    # =================================================================

    def update_experiment_status(
        self,
        recording: bool,
        elapsed_time_s: float,
        smoke_machine_active: bool,
        sequence_running: bool,
        sequence_step: Optional[int] = None,
    ) -> None:
        """
        Update recording, smoke-machine and sequence state.

        elapsed_time_s remains recording elapsed time.
        """

        # -------------------------------------------------------------
        # Smoke machine
        # -------------------------------------------------------------

        self._set_state_label(
            self.smoke_machine_state_label,
            smoke_machine_active,
        )

        # -------------------------------------------------------------
        # Recording
        # -------------------------------------------------------------

        if recording:

            self.recording_state_label.setText(
                "● Recording"
            )

            set_label_role(
                self.recording_state_label,
                "statusRecording",
            )

        else:

            self.recording_state_label.setText(
                "Not recording"
            )

            set_label_role(
                self.recording_state_label,
                "statusOff",
            )

        self.elapsed_time_label.setText(
            f"{float(elapsed_time_s):.1f} s"
        )

        # -------------------------------------------------------------
        # Sequence
        # -------------------------------------------------------------

        self._set_state_label(
            self.sequence_state_label,
            sequence_running,
            on_text="Running",
            off_text="Stopped",
        )

        if sequence_step is None:

            self.sequence_step_label.setText(
                "-"
            )

            set_label_role(
                self.sequence_step_label,
                "statusOff",
            )

        else:

            self.sequence_step_label.setText(
                f"Step {int(sequence_step)}"
            )

            set_label_role(
                self.sequence_step_label,
                "statusOn",
            )

    # =================================================================
    # LIVE PLOT STATE
    # =================================================================

    def update_live_plot_status(
        self,
        enabled: bool,
    ) -> None:
        """
        Update display-only Live Plot status.

        enabled=True:
            Graph is receiving new samples.

        enabled=False:
            Graph is frozen.

        Sensor measurements and recording are unaffected.
        """

        if enabled:

            self.live_plot_state_label.setText(
                "ON"
            )

            set_label_role(
                self.live_plot_state_label,
                "statusOn",
            )

            self.plot_window_label.setText(
                f"Last {config.LIVE_PLOT_TIME_WINDOW_S} s"
            )

        else:

            self.live_plot_state_label.setText(
                "FROZEN"
            )

            set_label_role(
                self.live_plot_state_label,
                "statusOff",
            )

            self.plot_window_label.setText(
                "Frozen"
            )

    # =================================================================
    # PUBLIC PLOT UPDATE
    # =================================================================

    def add_plot_sample(
        self,
        live_time_s: float,
        sensor_1_voltage: Optional[float],
        sensor_2_voltage: Optional[float],
    ) -> None:
        """
        Add one sample to compact live graph.

        MainWindow decides whether this method should be called.

        Therefore this widget does not itself decide whether plotting
        is enabled or frozen.
        """

        self._time_data.append(
            float(live_time_s)
        )

        # Sensor 1
        if sensor_1_voltage is None:

            self._sensor_1_data.append(
                float("nan")
            )

        else:

            self._sensor_1_data.append(
                float(sensor_1_voltage)
            )

        # Sensor 2
        if sensor_2_voltage is None:

            self._sensor_2_data.append(
                float("nan")
            )

        else:

            self._sensor_2_data.append(
                float(sensor_2_voltage)
            )

        times = list(
            self._time_data
        )

        self.sensor_1_curve.setData(
            times,
            list(
                self._sensor_1_data
            ),
        )

        self.sensor_2_curve.setData(
            times,
            list(
                self._sensor_2_data
            ),
        )

        # -------------------------------------------------------------
        # Rolling X window
        # -------------------------------------------------------------

        if times:

            latest_time = times[-1]

            earliest_visible = max(
                0.0,
                latest_time
                - config.LIVE_PLOT_TIME_WINDOW_S,
            )

            self.plot.setXRange(
                earliest_visible,
                max(
                    latest_time,
                    earliest_visible + 1.0,
                ),
                padding=0.0,
            )

    # =================================================================
    # CLEAR PLOT
    # =================================================================

    def clear_plots(
        self,
    ) -> None:
        """Clear all stored live-plot samples."""

        self._time_data.clear()
        self._sensor_1_data.clear()
        self._sensor_2_data.clear()

        self.sensor_1_curve.clear()
        self.sensor_2_curve.clear()

        self.plot.setXRange(
            0.0,
            min(
                10.0,
                float(
                    config.LIVE_PLOT_TIME_WINDOW_S
                ),
            ),
            padding=0.0,
        )

    # =================================================================
    # VOLTAGE FORMAT
    # =================================================================

    @staticmethod
    def _format_voltage(
        voltage: Optional[float],
    ) -> str:
        """Format voltage for display."""

        if voltage is None:
            return "-- V"

        return f"{float(voltage):.3f} V"