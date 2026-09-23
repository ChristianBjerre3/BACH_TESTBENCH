"""
gui/live_tab.py

Redesigned LIVE DATA interface for the Airflow Smoke Test Bench.

This tab is display-only.

It displays:
    - Sensor 1 state and live voltage
    - Sensor 2 state and live voltage
    - Main fan state, commanded PWM and measured RPM
    - Smoke fan state, commanded PWM and measured RPM
    - Smoke-machine manually logged state
    - Recording state and elapsed recording time
    - Sequence state and current sequence step
    - One combined Sensor 1 / Sensor 2 live graph
    - Sequence step-transition markers on the graph

It does NOT:
    - Read the ADC directly
    - Control GPIO
    - Control fans
    - Control LEDs
    - Start or stop recording
    - Run sequences

MainWindow pushes all current state and live data into this widget.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
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
    PAGE_MARGIN,
    CARD_SPACING,
    PLOT_BACKGROUND,
    PLOT_FOREGROUND,
    PLOT_GRID_ALPHA,
    SENSOR_1_COLOR,
    SENSOR_2_COLOR,
    SEQUENCE_MARKER_COLOR,
    PLOT_LINE_WIDTH,
)


class LiveTab(QWidget):
    """
    Main LIVE DATA dashboard.

    This widget only displays state/data supplied by MainWindow.
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

        self._main_rpm_data = deque(maxlen=max_points)
        self._smoke_rpm_data = deque(maxlen=max_points)

        # Graphics objects used for sequence-step markers.
        self._sequence_markers = []

        self._build_ui()

    # =================================================================
    # BUILD UI
    # =================================================================

    def _build_ui(self) -> None:
        """Build redesigned LIVE DATA dashboard."""

        main_layout = QHBoxLayout(
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
        # Left:
        # Main graph
        # -------------------------------------------------------------

        self.graph_card = (
            self._create_graph_card()
        )

        main_layout.addWidget(
            self.graph_card,
            stretch=3,
        )

        # -------------------------------------------------------------
        # Right:
        # Live values + system status + recording
        # -------------------------------------------------------------

        right_layout = QVBoxLayout()

        right_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        right_layout.setSpacing(
            CARD_SPACING
        )

        self.live_values_card = (
            self._create_live_values_card()
        )

        self.system_status_card = (
            self._create_system_status_card()
        )

        self.recording_card = (
            self._create_recording_card()
        )

        right_layout.addWidget(
            self.live_values_card
        )

        right_layout.addWidget(
            self.system_status_card,
            stretch=1,
        )

        right_layout.addWidget(
            self.recording_card
        )

        right_container = QWidget()

        right_container.setLayout(
            right_layout
        )

        right_container.setMinimumWidth(
            300
        )

        right_container.setMaximumWidth(
            430
        )

        main_layout.addWidget(
            right_container,
            stretch=1,
        )

    # =================================================================
    # CARD HELPERS
    # =================================================================

    @staticmethod
    def _new_card() -> QFrame:
        """Create a standard dashboard card."""

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
        """Create muted field label."""

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
        """Set label text and active/inactive styling."""

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
    # GRAPH CARD
    # =================================================================

    def _create_graph_card(
        self,
    ) -> QFrame:
        """Create main combined sensor graph."""

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

        # -------------------------------------------------------------
        # Header
        # -------------------------------------------------------------

        header = QHBoxLayout()

        title_area = QVBoxLayout()

        title_area.setSpacing(
            2
        )

        title_area.addWidget(
            self._card_title(
                "Sensor Live Data"
            )
        )

        subtitle = QLabel(
            "Optical sensor voltage over live experiment time"
        )

        set_label_role(
            subtitle,
            "muted",
        )

        title_area.addWidget(
            subtitle
        )

        header.addLayout(
            title_area
        )

        header.addStretch()

        window_label = QLabel(
            f"Live window: {config.LIVE_PLOT_TIME_WINDOW_S} s"
        )

        set_label_role(
            window_label,
            "muted",
        )

        header.addWidget(
            window_label
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

        self.plot.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.plot.setMinimumHeight(
            420
        )

        self.camera_preview_label = QLabel(
            "CAMERA OFF"
        )

        self.camera_preview_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.camera_preview_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self.camera_preview_label.setMinimumHeight(
            160
        )

        self.camera_preview_label.setMaximumHeight(
            260
        )

        self.camera_preview_label.setStyleSheet(
            """
            QLabel {
                background-color: #0A1825;
                border: 1px solid #243A4D;
                border-radius: 8px;
                color: #7F91A3;
                margin: 0px;
                padding: 0px;
            }
            """
        )

        # -------------------------------------------------------------
        # Axis appearance
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
            offset=(10, 10)
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

        self.plot.setYRange(0.0, 2.6, padding=0.0)

        # Initial visible time interval.
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

        layout.addWidget(
            self.plot,
            stretch=1,
        )

        # Dedicated RPM plot uses its own axis (RPM, never mixed with volts).
        self.rpm_plot = pg.PlotWidget()
        self.rpm_plot.setBackground(PLOT_BACKGROUND)
        self.rpm_plot.setLabel("left", "Fan speed", units="RPM")
        self.rpm_plot.setLabel("bottom", "Time", units="s")
        self.rpm_plot.showGrid(x=True, y=True, alpha=PLOT_GRID_ALPHA)
        self.rpm_plot.setMinimumHeight(130)
        self.rpm_plot.addLegend(offset=(10, 10))
        self.main_fan_rpm_curve = self.rpm_plot.plot(
            pen=pg.mkPen(SENSOR_1_COLOR, width=PLOT_LINE_WIDTH),
            name="Main fan RPM", connect="finite",
        )
        self.smoke_fan_rpm_curve = self.rpm_plot.plot(
            pen=pg.mkPen(SENSOR_2_COLOR, width=PLOT_LINE_WIDTH),
            name="Smoke fan RPM", connect="finite",
        )
        layout.addWidget(self.rpm_plot, stretch=0)

        layout.addWidget(
            self.camera_preview_label,
            stretch=0,
        )

        return card

    # =================================================================
    # LIVE VALUES CARD
    # =================================================================

    def _create_live_values_card(
        self,
    ) -> QFrame:
        """Create prominent Sensor 1 and Sensor 2 values."""

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
                "Live Values"
            )
        )

        # -------------------------------------------------------------
        # Sensor 1
        # -------------------------------------------------------------

        sensor_1_layout = QGridLayout()

        sensor_1_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.sensor_1_state_label = QLabel(
            "OFF"
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

        sensor_1_layout.addWidget(
            self._field_label(
                "Sensor 1"
            ),
            0,
            0,
        )

        sensor_1_layout.addWidget(
            self.sensor_1_state_label,
            0,
            1,
        )

        sensor_1_layout.addWidget(
            self.sensor_1_voltage_label,
            1,
            0,
            1,
            2,
        )

        layout.addLayout(
            sensor_1_layout
        )

        # Divider
        layout.addWidget(
            self._create_divider()
        )

        # -------------------------------------------------------------
        # Sensor 2
        # -------------------------------------------------------------

        sensor_2_layout = QGridLayout()

        sensor_2_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.sensor_2_state_label = QLabel(
            "OFF"
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

        sensor_2_layout.addWidget(
            self._field_label(
                "Sensor 2"
            ),
            0,
            0,
        )

        sensor_2_layout.addWidget(
            self.sensor_2_state_label,
            0,
            1,
        )

        sensor_2_layout.addWidget(
            self.sensor_2_voltage_label,
            1,
            0,
            1,
            2,
        )

        layout.addLayout(
            sensor_2_layout
        )

        return card

    # =================================================================
    # SYSTEM STATUS CARD
    # =================================================================

    def _create_system_status_card(
        self,
    ) -> QFrame:
        """Create complete experiment/system state card."""

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
                "System Status"
            )
        )

        grid = QGridLayout()

        grid.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        grid.setHorizontalSpacing(
            8
        )

        grid.setVerticalSpacing(
            9
        )

        # -------------------------------------------------------------
        # Main fan
        # -------------------------------------------------------------

        self.main_fan_state_label = QLabel(
            "OFF"
        )

        self.main_fan_pwm_label = QLabel(
            "0 %"
        )

        self.main_fan_pwm_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        # -------------------------------------------------------------
        # Smoke fan
        # -------------------------------------------------------------

        self.smoke_fan_state_label = QLabel(
            "OFF"
        )

        self.smoke_fan_pwm_label = QLabel(
            "0 %"
        )

        self.smoke_fan_pwm_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        self.main_fan_rpm_label = QLabel("-- RPM")
        self.smoke_fan_rpm_label = QLabel("-- RPM")
        for label in (self.main_fan_rpm_label, self.smoke_fan_rpm_label):
            label.setAlignment(Qt.AlignmentFlag.AlignRight)


        # -------------------------------------------------------------
        # Smoke machine
        # -------------------------------------------------------------

        self.smoke_machine_state_label = QLabel(
            "OFF"
        )

        # -------------------------------------------------------------
        # Recording
        # -------------------------------------------------------------

        self.recording_state_label = QLabel(
            "Not recording"
        )

        # -------------------------------------------------------------
        # Sequence
        # -------------------------------------------------------------

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
        # Rows
        # -------------------------------------------------------------

        row = 0

        row = self._add_status_row(
            grid,
            row,
            "Main fan",
            self.main_fan_state_label,
            self.main_fan_pwm_label,
        )

        row = self._add_status_row(
            grid, row, "Main fan measured", QLabel("FG"), self.main_fan_rpm_label,
        )

        row = self._add_status_row(
            grid,
            row,
            "Smoke fan",
            self.smoke_fan_state_label,
            self.smoke_fan_pwm_label,
        )

        row = self._add_status_row(
            grid, row, "Smoke fan measured", QLabel("FG"), self.smoke_fan_rpm_label,
        )

        row = self._add_status_row(
            grid,
            row,
            "Smoke machine",
            self.smoke_machine_state_label,
            None,
        )

        row = self._add_status_row(
            grid,
            row,
            "Recording",
            self.recording_state_label,
            None,
        )

        self._add_status_row(
            grid,
            row,
            "Sequence",
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

        layout.addLayout(
            grid
        )

        layout.addStretch()

        return card

    # =================================================================
    # RECORDING CARD
    # =================================================================

    def _create_recording_card(
        self,
    ) -> QFrame:
        """Create recording state / timer card."""

        card = self._new_card()

        layout = QHBoxLayout(
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

        text_layout = QVBoxLayout()

        text_layout.setSpacing(
            2
        )

        text_layout.addWidget(
            self._card_title(
                "Recording"
            )
        )

        self.recording_bottom_state_label = QLabel(
            "Not recording"
        )

        set_label_role(
            self.recording_bottom_state_label,
            "statusOff",
        )

        text_layout.addWidget(
            self.recording_bottom_state_label
        )

        layout.addLayout(
            text_layout
        )

        layout.addStretch()

        self.elapsed_time_label = QLabel(
            "0.0 s"
        )

        set_label_role(
            self.elapsed_time_label,
            "timer",
        )

        layout.addWidget(
            self.elapsed_time_label
        )

        return card

    # =================================================================
    # HELPERS
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
        """Add one row to the system-status grid."""

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
    # SENSOR VALUES
    # =================================================================

    def update_sensor_values(
        self,
        sensor_1_active: bool,
        sensor_1_voltage: Optional[float],
        sensor_2_active: bool,
        sensor_2_voltage: Optional[float],
    ) -> None:
        """Update Sensor 1 and Sensor 2 numerical displays."""

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
    # FAN VALUES
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
        """Update commanded fan state and independently measured RPM."""

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

        self.main_fan_rpm_label.setText(self._format_rpm(main_fan_rpm))
        self.smoke_fan_rpm_label.setText(self._format_rpm(smoke_fan_rpm))

    # =================================================================
    # EXPERIMENT STATUS
    # =================================================================

    def update_experiment_status(
        self,
        recording: bool,
        elapsed_time_s: float,
        smoke_machine_active: bool,
        sequence_running: bool,
        sequence_step: Optional[int] = None,
    ) -> None:
        """Update recording, smoke-machine and sequence state."""

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

            self.recording_bottom_state_label.setText(
                "● RECORDING"
            )

            set_label_role(
                self.recording_state_label,
                "statusRecording",
            )

            set_label_role(
                self.recording_bottom_state_label,
                "statusRecording",
            )

        else:

            self.recording_state_label.setText(
                "Not recording"
            )

            self.recording_bottom_state_label.setText(
                "Not recording"
            )

            set_label_role(
                self.recording_state_label,
                "statusOff",
            )

            set_label_role(
                self.recording_bottom_state_label,
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
    # PLOT DATA
    # =================================================================

    def add_plot_sample(
        self,
        live_time_s: float,
        sensor_1_voltage: Optional[float],
        sensor_2_voltage: Optional[float],
        main_fan_rpm: Optional[float] = None,
        smoke_fan_rpm: Optional[float] = None,
    ) -> None:
        """
        Add one sample to the combined graph.

        live_time_s is the GUI live timebase supplied by MainWindow.

        None values are stored as NaN so the graph contains a gap
        rather than drawing a false zero value.
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

        # Separate RPM history: missing FG readings become plot gaps.
        self._main_rpm_data.append(
            float(main_fan_rpm) if main_fan_rpm is not None else float("nan")
        )
        self._smoke_rpm_data.append(
            float(smoke_fan_rpm) if smoke_fan_rpm is not None else float("nan")
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

        self.main_fan_rpm_curve.setData(times, list(self._main_rpm_data))
        self.smoke_fan_rpm_curve.setData(times, list(self._smoke_rpm_data))

        # -------------------------------------------------------------
        # Maintain configured rolling X window
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
            self.plot.setYRange(0.0, 2.6, padding=0.0)
            self.rpm_plot.setXRange(
                earliest_visible, max(latest_time, earliest_visible + 1.0), padding=0.0,
            )

    # =================================================================
    # SEQUENCE STEP MARKERS
    # =================================================================

    def add_sequence_step_marker(
        self,
        live_time_s: float,
        step_number: int,
    ) -> None:
        """
        Add a vertical graph marker when a sequence step begins.

        Example:
            Step 1 at t = 0 s
            Step 2 at t = 5 s
            Step 3 at t = 12 s

        MainWindow decides when a step transition occurs and supplies
        the live time and step number.
        """

        time_value = float(
            live_time_s
        )

        step_value = int(
            step_number
        )

        # -------------------------------------------------------------
        # Vertical line
        # -------------------------------------------------------------

        line = pg.InfiniteLine(
            pos=time_value,
            angle=90,
            movable=False,
            pen=pg.mkPen(
                SEQUENCE_MARKER_COLOR,
                width=1,
                style=Qt.PenStyle.DashLine,
            ),
        )

        line.setZValue(
            10
        )

        self.plot.addItem(
            line
        )

        # -------------------------------------------------------------
        # Step label
        # -------------------------------------------------------------

        label = pg.TextItem(
            text=f"Step {step_value}",
            color=SEQUENCE_MARKER_COLOR,
            anchor=(0, 0),
        )

        label.setZValue(
            11
        )

        # Position the text close to the top of the current plot.
        view_range = (
            self.plot.getViewBox().viewRange()
        )

        y_min, y_max = (
            view_range[1]
        )

        y_position = (
            y_max
            - 0.05
            * max(
                y_max - y_min,
                1.0,
            )
        )

        label.setPos(
            time_value,
            y_position,
        )

        self.plot.addItem(
            label
        )

        # Store both so they can be removed on reset.
        self._sequence_markers.append(
            (
                line,
                label,
            )
        )

    # =================================================================
    # CLEAR PLOTS
    # =================================================================

    def set_camera_preview(
        self,
        frame,
        available: bool,
    ) -> None:
        """Display the current camera preview or a neutral placeholder without resizing layout."""

        empty_pixmap = QPixmap()

        if frame is None:
            self.camera_preview_label.setPixmap(empty_pixmap)
            self.camera_preview_label.setText("CAMERA OFF")
            return

        if not available:
            self.camera_preview_label.setPixmap(empty_pixmap)
            self.camera_preview_label.setText("CAMERA OFF")
            return

        try:
            import cv2

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w

            qimage = QImage(
                rgb.data,
                w,
                h,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            )
            pixmap = QPixmap.fromImage(qimage)
            target_size = self.camera_preview_label.size()
            if target_size.width() <= 1 or target_size.height() <= 1:
                target_size = self.camera_preview_label.sizeHint()

            scaled = pixmap.scaled(
                target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.camera_preview_label.setPixmap(scaled)
            self.camera_preview_label.setText("")
        except Exception:
            self.camera_preview_label.setText("CAMERA NOT AVAILABLE")
            self.camera_preview_label.setPixmap(empty_pixmap)

    def clear_plots(
        self,
    ) -> None:
        """
        Clear:
            - Sensor history
            - Sensor curves
            - Sequence step markers

        The graph X-axis is visually reset to start at 0 s.

        MainWindow is responsible for resetting the live-time epoch itself.
        """

        # -------------------------------------------------------------
        # Data
        # -------------------------------------------------------------

        self._time_data.clear()
        self._sensor_1_data.clear()
        self._sensor_2_data.clear()
        self._main_rpm_data.clear()
        self._smoke_rpm_data.clear()
        self.main_fan_rpm_curve.clear()
        self.smoke_fan_rpm_curve.clear()

        self.sensor_1_curve.clear()
        self.sensor_2_curve.clear()

        # -------------------------------------------------------------
        # Sequence markers
        # -------------------------------------------------------------

        for line, label in self._sequence_markers:

            try:
                self.plot.removeItem(
                    line
                )
            except Exception:
                pass

            try:
                self.plot.removeItem(
                    label
                )
            except Exception:
                pass

        self._sequence_markers.clear()

        # -------------------------------------------------------------
        # Reset visible graph time
        # -------------------------------------------------------------

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
        self.plot.setYRange(0.0, 2.6, padding=0.0)
        self.rpm_plot.setXRange(
            0.0, min(10.0, float(config.LIVE_PLOT_TIME_WINDOW_S)), padding=0.0,
        )

    # =================================================================
    # VOLTAGE FORMAT
    # =================================================================

    @staticmethod
    def _format_voltage(
        voltage: Optional[float],
    ) -> str:
        """Format sensor voltage."""

        if voltage is None:
            return "-- V"

        return f"{float(voltage):.3f} V"

    @staticmethod
    def _format_rpm(rpm: Optional[float]) -> str:
        """Unknown measurement remains unknown, never a fabricated zero."""
        if rpm is None:
            return "-- RPM"
        return f"{float(rpm):,.0f} RPM".replace(",", " ")
