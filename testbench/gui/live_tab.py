"""
gui/live_tab.py

Live data tab for the airflow/smoke test bench GUI.

This tab displays:
    - Sensor 1 voltage
    - Sensor 2 voltage
    - Main fan state and PWM
    - Smoke fan state and PWM
    - Manual smoke-machine state
    - Recording elapsed time
    - Sequence state
    - Live plots for both optical sensors

This module only displays data.

It does NOT:
    - Read the ADC directly
    - Control GPIO
    - Control fans
    - Control LEDs
    - Start or stop recording

The MainWindow will later update this tab with the current
TestSession and sensor values.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

import pyqtgraph as pg

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
)

import config


class LiveTab(QWidget):
    """
    Live measurement and status display.
    """

    def __init__(self, parent=None) -> None:
        """
        Initialize the Live Data tab.
        """

        super().__init__(parent)

        # ------------------------------------------------------------
        # Plot data storage
        # ------------------------------------------------------------

        max_points = int(
            config.LIVE_PLOT_TIME_WINDOW_S
            * config.SENSOR_SAMPLE_RATE_HZ
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

        self._build_ui()

    # ================================================================
    # BUILD UI
    # ================================================================

    def _build_ui(self) -> None:
        """
        Create all widgets and layouts.
        """

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)
        status_layout.addWidget(self._create_sensor_status_group())
        status_layout.addWidget(self._create_fan_status_group())
        main_layout.addLayout(status_layout)

        main_layout.addWidget(self._create_experiment_status_group())
        main_layout.addWidget(self._create_sensor_1_plot_group(), stretch=1)
        main_layout.addWidget(self._create_sensor_2_plot_group(), stretch=1)

    # ================================================================
    # SENSOR STATUS
    # ================================================================

    def _create_sensor_status_group(
        self,
    ) -> QGroupBox:
        """
        Create numerical optical-sensor displays.
        """

        group = QGroupBox(
            "Optical sensors"
        )

        layout = QGridLayout(group)

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

        self.sensor_1_voltage_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        self.sensor_2_voltage_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        layout.addWidget(
            QLabel("Sensor 1:"),
            0,
            0,
        )

        layout.addWidget(
            self.sensor_1_state_label,
            0,
            1,
        )

        layout.addWidget(
            self.sensor_1_voltage_label,
            0,
            2,
        )

        layout.addWidget(
            QLabel("Sensor 2:"),
            1,
            0,
        )

        layout.addWidget(
            self.sensor_2_state_label,
            1,
            1,
        )

        layout.addWidget(
            self.sensor_2_voltage_label,
            1,
            2,
        )

        return group

    # ================================================================
    # FAN STATUS
    # ================================================================

    def _create_fan_status_group(
        self,
    ) -> QGroupBox:
        """
        Create main-fan and smoke-fan status display.
        """

        group = QGroupBox(
            "Fans"
        )

        layout = QGridLayout(group)

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

        layout.addWidget(
            QLabel("Main fan:"),
            0,
            0,
        )

        layout.addWidget(
            self.main_fan_state_label,
            0,
            1,
        )

        layout.addWidget(
            QLabel("PWM:"),
            0,
            2,
        )

        layout.addWidget(
            self.main_fan_pwm_label,
            0,
            3,
        )

        layout.addWidget(
            QLabel("Smoke fan:"),
            1,
            0,
        )

        layout.addWidget(
            self.smoke_fan_state_label,
            1,
            1,
        )

        layout.addWidget(
            QLabel("PWM:"),
            1,
            2,
        )

        layout.addWidget(
            self.smoke_fan_pwm_label,
            1,
            3,
        )

        return group

    # ================================================================
    # EXPERIMENT STATUS
    # ================================================================

    def _create_experiment_status_group(
        self,
    ) -> QGroupBox:
        """
        Create recording, smoke-machine and sequence status.
        """

        group = QGroupBox(
            "Experiment status"
        )

        layout = QGridLayout(group)

        self.recording_state_label = QLabel(
            "Not recording"
        )

        self.elapsed_time_label = QLabel(
            "0.0 s"
        )

        self.smoke_machine_state_label = QLabel(
            "OFF"
        )

        self.sequence_state_label = QLabel(
            "Stopped"
        )

        self.sequence_step_label = QLabel(
            "-"
        )

        layout.addWidget(
            QLabel("Recording:"),
            0,
            0,
        )

        layout.addWidget(
            self.recording_state_label,
            0,
            1,
        )

        layout.addWidget(
            QLabel("Elapsed time:"),
            0,
            2,
        )

        layout.addWidget(
            self.elapsed_time_label,
            0,
            3,
        )

        layout.addWidget(
            QLabel("Smoke machine:"),
            1,
            0,
        )

        layout.addWidget(
            self.smoke_machine_state_label,
            1,
            1,
        )

        layout.addWidget(
            QLabel("Sequence:"),
            1,
            2,
        )

        layout.addWidget(
            self.sequence_state_label,
            1,
            3,
        )

        layout.addWidget(
            QLabel("Sequence step:"),
            2,
            2,
        )

        layout.addWidget(
            self.sequence_step_label,
            2,
            3,
        )

        return group

    # ================================================================
    # SENSOR 1 PLOT
    # ================================================================

    def _create_sensor_1_plot_group(
        self,
    ) -> QGroupBox:
        """
        Create live voltage plot for Sensor 1.
        """

        group = QGroupBox(
            "Sensor 1 live voltage"
        )

        layout = QVBoxLayout(group)

        self.sensor_1_plot = pg.PlotWidget()

        self.sensor_1_plot.setLabel(
            "left",
            "Voltage",
            units="V",
        )

        self.sensor_1_plot.setLabel(
            "bottom",
            "Time",
            units="s",
        )

        self.sensor_1_plot.showGrid(
            x=True,
            y=True,
            alpha=0.3,
        )

        self.sensor_1_curve = (
            self.sensor_1_plot.plot()
        )

        layout.addWidget(
            self.sensor_1_plot
        )

        return group

    # ================================================================
    # SENSOR 2 PLOT
    # ================================================================

    def _create_sensor_2_plot_group(
        self,
    ) -> QGroupBox:
        """
        Create live voltage plot for Sensor 2.
        """

        group = QGroupBox(
            "Sensor 2 live voltage"
        )

        layout = QVBoxLayout(group)

        self.sensor_2_plot = pg.PlotWidget()

        self.sensor_2_plot.setLabel(
            "left",
            "Voltage",
            units="V",
        )

        self.sensor_2_plot.setLabel(
            "bottom",
            "Time",
            units="s",
        )

        self.sensor_2_plot.showGrid(
            x=True,
            y=True,
            alpha=0.3,
        )

        self.sensor_2_curve = (
            self.sensor_2_plot.plot()
        )

        layout.addWidget(
            self.sensor_2_plot
        )

        return group

    # ================================================================
    # SENSOR VALUES
    # ================================================================

    def update_sensor_values(
        self,
        sensor_1_active: bool,
        sensor_1_voltage: Optional[float],
        sensor_2_active: bool,
        sensor_2_voltage: Optional[float],
    ) -> None:
        """
        Update numerical sensor display.

        Parameters
        ----------
        sensor_1_active:
            Current Sensor 1 active state.

        sensor_1_voltage:
            Current Sensor 1 voltage or None.

        sensor_2_active:
            Current Sensor 2 active state.

        sensor_2_voltage:
            Current Sensor 2 voltage or None.
        """

        self.sensor_1_state_label.setText(
            "ON" if sensor_1_active else "OFF"
        )

        self.sensor_2_state_label.setText(
            "ON" if sensor_2_active else "OFF"
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
    # FAN VALUES
    # ================================================================

    def update_fan_status(
        self,
        main_fan_active: bool,
        main_fan_pwm_percent: int,
        smoke_fan_active: bool,
        smoke_fan_pwm_percent: int,
    ) -> None:
        """
        Update fan state and PWM displays.
        """

        self.main_fan_state_label.setText(
            "ON"
            if main_fan_active
            else "OFF"
        )

        self.main_fan_pwm_label.setText(
            f"{main_fan_pwm_percent} %"
        )

        self.smoke_fan_state_label.setText(
            "ON"
            if smoke_fan_active
            else "OFF"
        )

        self.smoke_fan_pwm_label.setText(
            f"{smoke_fan_pwm_percent} %"
        )

    # ================================================================
    # EXPERIMENT STATUS
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
        Update general experiment status.
        """

        self.recording_state_label.setText(
            "Recording"
            if recording
            else "Not recording"
        )

        self.elapsed_time_label.setText(
            f"{elapsed_time_s:.1f} s"
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
                str(sequence_step)
            )

    # ================================================================
    # PLOT DATA
    # ================================================================

    def add_plot_sample(
        self,
        elapsed_time_s: float,
        sensor_1_voltage: Optional[float],
        sensor_2_voltage: Optional[float],
    ) -> None:
        """
        Add one new sample to the live plots.

        None values are stored as NaN so pyqtgraph leaves a gap
        instead of drawing a false zero measurement.
        """

        self._time_data.append(
            float(elapsed_time_s)
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

        self.sensor_1_curve.setData(
            list(self._time_data),
            list(self._sensor_1_data),
        )

        self.sensor_2_curve.setData(
            list(self._time_data),
            list(self._sensor_2_data),
        )

    def clear_plots(self) -> None:
        """
        Clear all stored live-plot data.
        """

        self._time_data.clear()
        self._sensor_1_data.clear()
        self._sensor_2_data.clear()

        self.sensor_1_curve.clear()
        self.sensor_2_curve.clear()

    # ================================================================
    # HELPERS
    # ================================================================

    @staticmethod
    def _format_voltage(
        voltage: Optional[float],
    ) -> str:
        """
        Format a sensor voltage for display.
        """

        if voltage is None:
            return "-- V"

        return f"{voltage:.4f} V"