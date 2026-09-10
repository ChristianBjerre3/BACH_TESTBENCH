"""
gui/live_status_panel.py

Compact live status panel used by CONTROL and SEQUENCE.

The panel displays:
    - Sensor states and voltages
    - Fan states and PWM
    - Smoke-machine log state
    - Recording state and elapsed recording time
    - Sequence state/current step
    - Compact combined Sensor 1 / Sensor 2 live plot

IMPORTANT:
This widget is display-only.

It does NOT:
    - Read the ADC
    - Control hardware
    - Control sensors
    - Control fans
    - Start/stop recording
    - Run sequences

MainWindow pushes data into this widget.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QSizePolicy,
)

import config


class LiveStatusPanel(QWidget):
    """
    Compact live-data side panel.

    One instance can be used beside CONTROL and another beside SEQUENCE.
    Both receive the same sample data from MainWindow.
    """

    # ================================================================
    # INITIALIZATION
    # ================================================================

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

        self.setMinimumWidth(270)
        self.setMaximumWidth(380)

        self._build_ui()

    # ================================================================
    # BUILD UI
    # ================================================================

    def _build_ui(self) -> None:
        """Build compact status and plot layout."""

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            4,
            4,
            4,
            4,
        )

        layout.setSpacing(6)

        # ------------------------------------------------------------
        # Title
        # ------------------------------------------------------------

        title = QLabel(
            "LIVE STATUS"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title.setStyleSheet(
            """
            QLabel {
                font-size: 13px;
                font-weight: bold;
                padding: 2px;
            }
            """
        )

        layout.addWidget(
            title
        )

        # ------------------------------------------------------------
        # Status
        # ------------------------------------------------------------

        layout.addWidget(
            self._create_status_group()
        )

        # ------------------------------------------------------------
        # Plot
        # ------------------------------------------------------------

        layout.addWidget(
            self._create_plot_group(),
            stretch=1,
        )

    # ================================================================
    # STATUS GROUP
    # ================================================================

    def _create_status_group(
        self,
    ) -> QGroupBox:
        """Create compact textual live status."""

        group = QGroupBox(
            "Status"
        )

        grid = QGridLayout(
            group
        )

        grid.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        grid.setHorizontalSpacing(
            8
        )

        grid.setVerticalSpacing(
            4
        )

        # ------------------------------------------------------------
        # Sensor labels
        # ------------------------------------------------------------

        self.sensor_1_state_label = QLabel(
            "OFF"
        )

        self.sensor_1_voltage_label = QLabel(
            "-- V"
        )

        self.sensor_2_state_label = QLabel(
            "OFF"
        )

        self.sensor_2_voltage_label = QLabel(
            "-- V"
        )

        # ------------------------------------------------------------
        # Fan labels
        # ------------------------------------------------------------

        self.main_fan_state_label = QLabel(
            "OFF"
        )

        self.main_fan_pwm_label = QLabel(
            "0 %"
        )

        self.smoke_fan_state_label = QLabel(
            "OFF"
        )

        self.smoke_fan_pwm_label = QLabel(
            "0 %"
        )

        # ------------------------------------------------------------
        # Experiment labels
        # ------------------------------------------------------------

        self.smoke_machine_state_label = QLabel(
            "OFF"
        )

        self.recording_state_label = QLabel(
            "Not recording"
        )

        self.elapsed_time_label = QLabel(
            "0.0 s"
        )

        self.sequence_state_label = QLabel(
            "Stopped"
        )

        self.sequence_step_label = QLabel(
            "-"
        )

        # Make measurements easy to identify visually.
        self.sensor_1_voltage_label.setStyleSheet(
            "font-weight: bold;"
        )

        self.sensor_2_voltage_label.setStyleSheet(
            "font-weight: bold;"
        )

        # ------------------------------------------------------------
        # Rows
        # ------------------------------------------------------------

        row = 0

        row = self._add_row(
            grid,
            row,
            "Sensor 1:",
            self.sensor_1_state_label,
            self.sensor_1_voltage_label,
        )

        row = self._add_row(
            grid,
            row,
            "Sensor 2:",
            self.sensor_2_state_label,
            self.sensor_2_voltage_label,
        )

        row = self._add_row(
            grid,
            row,
            "Main fan:",
            self.main_fan_state_label,
            self.main_fan_pwm_label,
        )

        row = self._add_row(
            grid,
            row,
            "Smoke fan:",
            self.smoke_fan_state_label,
            self.smoke_fan_pwm_label,
        )

        row = self._add_row(
            grid,
            row,
            "Smoke machine:",
            self.smoke_machine_state_label,
            None,
        )

        row = self._add_row(
            grid,
            row,
            "Recording:",
            self.recording_state_label,
            self.elapsed_time_label,
        )

        self._add_row(
            grid,
            row,
            "Sequence:",
            self.sequence_state_label,
            self.sequence_step_label,
        )

        grid.setColumnStretch(
            0,
            1,
        )

        grid.setColumnStretch(
            1,
            1,
        )

        grid.setColumnStretch(
            2,
            1,
        )

        return group

    # ================================================================
    # STATUS ROW HELPER
    # ================================================================

    @staticmethod
    def _add_row(
        grid: QGridLayout,
        row: int,
        title: str,
        value_a: QLabel,
        value_b: Optional[QLabel],
    ) -> int:
        """Add one row to the status grid."""

        grid.addWidget(
            QLabel(title),
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

    # ================================================================
    # LIVE PLOT
    # ================================================================

    def _create_plot_group(
        self,
    ) -> QGroupBox:
        """Create combined compact Sensor 1 / Sensor 2 plot."""

        group = QGroupBox(
            f"Sensors - last {config.LIVE_PLOT_TIME_WINDOW_S} s"
        )

        layout = QVBoxLayout(
            group
        )

        layout.setContentsMargins(
            4,
            4,
            4,
            4,
        )

        self.plot = pg.PlotWidget()

        self.plot.setLabel(
            "left",
            "Voltage",
            units="V",
        )

        self.plot.setLabel(
            "bottom",
            "Live time",
            units="s",
        )

        self.plot.showGrid(
            x=True,
            y=True,
            alpha=0.3,
        )

        self.plot.addLegend(
            offset=(8, 8)
        )

        self.plot.setMinimumHeight(
            140
        )

        self.plot.setMaximumHeight(
            220
        )

        self.plot.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        # ------------------------------------------------------------
        # Curves
        #
        # Colours are deliberately different so the two sensors can
        # be distinguished quickly during a physical experiment.
        # ------------------------------------------------------------

        self.sensor_1_curve = self.plot.plot(
            pen=pg.mkPen(
                "#1f77b4",
                width=2,
            ),
            name="Sensor 1",
            connect="finite",
        )

        self.sensor_2_curve = self.plot.plot(
            pen=pg.mkPen(
                "#d62728",
                width=2,
            ),
            name="Sensor 2",
            connect="finite",
        )

        layout.addWidget(
            self.plot
        )

        return group

    # ================================================================
    # PUBLIC SENSOR UPDATE
    # ================================================================

    def update_sensor_values(
        self,
        sensor_1_active: bool,
        sensor_1_voltage: Optional[float],
        sensor_2_active: bool,
        sensor_2_voltage: Optional[float],
    ) -> None:
        """Update sensor state and voltage labels."""

        self.sensor_1_state_label.setText(
            "ON"
            if sensor_1_active
            else "OFF"
        )

        self.sensor_2_state_label.setText(
            "ON"
            if sensor_2_active
            else "OFF"
        )

        self.sensor_1_voltage_label.setText(
            self._format_voltage(
                sensor_1_voltage
            )
        )

        self.sensor_2_voltage_label.setText(
            self._format_voltage(
                sensor_2_voltage
            )
        )

    # ================================================================
    # PUBLIC FAN UPDATE
    # ================================================================

    def update_fan_status(
        self,
        main_fan_active: bool,
        main_fan_pwm_percent: int,
        smoke_fan_active: bool,
        smoke_fan_pwm_percent: int,
    ) -> None:
        """Update both fan states and PWM values."""

        self.main_fan_state_label.setText(
            "ON"
            if main_fan_active
            else "OFF"
        )

        self.main_fan_pwm_label.setText(
            f"{int(main_fan_pwm_percent)} %"
        )

        self.smoke_fan_state_label.setText(
            "ON"
            if smoke_fan_active
            else "OFF"
        )

        self.smoke_fan_pwm_label.setText(
            f"{int(smoke_fan_pwm_percent)} %"
        )

    # ================================================================
    # PUBLIC EXPERIMENT STATUS UPDATE
    # ================================================================

    def update_experiment_status(
        self,
        recording: bool,
        elapsed_time_s: float,
        smoke_machine_active: bool,
        sequence_running: bool,
        sequence_step: Optional[int] = None,
    ) -> None:
        """
        Update recording, smoke-machine, and sequence status.

        elapsed_time_s is recording elapsed time.

        It is intentionally separate from the live-plot time supplied
        to add_plot_sample().
        """

        self.recording_state_label.setText(
            "Recording"
            if recording
            else "Not recording"
        )

        self.elapsed_time_label.setText(
            f"{float(elapsed_time_s):.1f} s"
        )

        self.smoke_machine_state_label.setText(
            "ON"
            if smoke_machine_active
            else "OFF"
        )

        self.sequence_state_label.setText(
            "Running"
            if sequence_running
            else "Stopped"
        )

        if sequence_step is None:

            self.sequence_step_label.setText(
                "-"
            )

        else:

            self.sequence_step_label.setText(
                f"Step {int(sequence_step)}"
            )

    # ================================================================
    # PUBLIC PLOT UPDATE
    # ================================================================

    def add_plot_sample(
        self,
        live_time_s: float,
        sensor_1_voltage: Optional[float],
        sensor_2_voltage: Optional[float],
    ) -> None:
        """
        Add one sample to the compact live graph.

        IMPORTANT:
        live_time_s is a GUI/live timebase supplied by MainWindow.

        It is NOT recording elapsed time.

        This allows the graph to continue working:
            - before recording
            - during recording
            - after recording
            - during unrecorded sequences
        """

        self._time_data.append(
            float(live_time_s)
        )

        if sensor_1_voltage is None:

            self._sensor_1_data.append(
                float("nan")
            )

        else:

            self._sensor_1_data.append(
                float(sensor_1_voltage)
            )

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
            list(self._sensor_1_data),
        )

        self.sensor_2_curve.setData(
            times,
            list(self._sensor_2_data),
        )

        # Keep the X-axis focused on the configured live window.
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

    # ================================================================
    # CLEAR PLOT
    # ================================================================

    def clear_plots(
        self,
    ) -> None:
        """Clear all stored live-plot samples."""

        self._time_data.clear()
        self._sensor_1_data.clear()
        self._sensor_2_data.clear()

        self.sensor_1_curve.clear()
        self.sensor_2_curve.clear()

    # ================================================================
    # VOLTAGE FORMAT
    # ================================================================

    @staticmethod
    def _format_voltage(
        voltage: Optional[float],
    ) -> str:
        """Format voltage for display."""

        if voltage is None:
            return "-- V"

        return f"{float(voltage):.3f} V"