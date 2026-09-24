"""
services/logger.py

Data logging for the airflow/smoke test bench.

Each recorded experiment can create three files:

1. <base>.csv
   Continuous 10 Hz time-series data.

2. <base>_metadata.json
   Metadata describing the experiment.

3. <base>_events.csv
   Discrete state-change events that occur while recording.

DataLogger does NOT own a timer.

MainWindow is responsible for:
    - Calling log_sample() at the configured sample rate.
    - Calling log_event() when discrete state changes occur.
"""

from __future__ import annotations

import csv
import json
import re

from datetime import datetime
from pathlib import Path
from typing import Optional, Any

import time

import config

from services.test_session import TestSession


# ====================================================================
# EVENT CSV FORMAT
# ====================================================================

EVENT_COLUMNS = (
    "timestamp",
    "elapsed_time_s",
    "event",
    "details",
)


# ====================================================================
# DATA LOGGER
# ====================================================================


class DataLogger:
    """
    Manage recording files for one TestSession.

    A DataLogger instance can be reused for multiple recordings.
    Each call to start() creates a new set of files.
    """

    def __init__(
        self,
        session: TestSession,
        data_directory: Optional[str | Path] = None,
    ) -> None:
        """Initialize logger."""

        self.session = session

        if data_directory is None:
            data_directory = config.DATA_DIRECTORY

        self.data_directory = Path(
            data_directory
        )

        # ------------------------------------------------------------
        # Time-series file
        # ------------------------------------------------------------

        self._csv_file = None
        self._csv_writer: Optional[csv.DictWriter] = None
        self._csv_path: Optional[Path] = None

        # ------------------------------------------------------------
        # Metadata file
        # ------------------------------------------------------------

        self._metadata_path: Optional[Path] = None

        # ------------------------------------------------------------
        # Event file
        # ------------------------------------------------------------

        self._event_file = None
        self._event_writer: Optional[csv.DictWriter] = None
        self._events_path: Optional[Path] = None

        # ------------------------------------------------------------
        # Video files
        # ------------------------------------------------------------

        self._video_path: Optional[Path] = None
        self._video_2_path: Optional[Path] = None
        self._video_timestamps_path: Optional[Path] = None
        self._video_timestamps_file = None
        self._video_timestamps_writer: Optional[csv.DictWriter] = None
        self._base_name: Optional[str] = None

        # ------------------------------------------------------------
        # Camera metadata state
        # ------------------------------------------------------------

        self._camera_available = False
        self._camera_index = None
        self._camera_auto_exposure = None
        self._camera_exposure = None
        self._camera_gain = None
        self._video_recorded = False

        # ------------------------------------------------------------
        # State
        # ------------------------------------------------------------

        self._recording = False

        # Periodic flush counter.
        #
        # We do not flush every single 10 Hz sample because that causes
        # unnecessary disk I/O, but we also do not want a large amount
        # of buffered data to be lost if the program exits unexpectedly.
        self._samples_since_flush = 0

        self._flush_every_n_samples = max(
            1,
            int(config.SENSOR_SAMPLE_RATE_HZ),
        )

    # =================================================================
    # START RECORDING
    # =================================================================

    def start(self) -> Path:
        """
        Start a new recording.

        Creates:
            - time-series CSV
            - metadata JSON
            - events CSV

        Returns the path of the time-series CSV.
        """

        if self._recording:
            raise RuntimeError(
                "A recording is already active."
            )

        # Make sure any stale handles from an earlier interrupted
        # recording are closed before creating new files.
        self._close_files()

        self.data_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ------------------------------------------------------------
        # Start session timer first
        # ------------------------------------------------------------

        self.session.start_recording()

        # ------------------------------------------------------------
        # Create unique base filename
        # ------------------------------------------------------------

        base_name = self._create_base_filename()
        self._base_name = base_name

        self._csv_path = (
            self.data_directory
            / f"{base_name}{config.CSV_FILE_EXTENSION}"
        )

        self._metadata_path = (
            self.data_directory
            / f"{base_name}_metadata.json"
        )

        self._events_path = (
            self.data_directory
            / f"{base_name}_events.csv"
        )

        self._video_path = (
            self.data_directory
            / f"{base_name}_video{config.VIDEO_FILE_EXTENSION}"
        )

        self._video_2_path = (
            self.data_directory
            / f"{base_name}_video_cam2{config.VIDEO_FILE_EXTENSION}"
        )

        self._video_timestamps_path = (
            self.data_directory
            / f"{base_name}_video_timestamps.csv"
        )

        try:

            # --------------------------------------------------------
            # Time-series CSV
            # --------------------------------------------------------

            self._csv_file = self._csv_path.open(
                mode="w",
                newline="",
                encoding="utf-8",
            )

            self._csv_writer = csv.DictWriter(
                self._csv_file,
                fieldnames=config.CSV_COLUMNS,
                delimiter=config.CSV_DELIMITER,
            )

            self._csv_writer.writeheader()

            # --------------------------------------------------------
            # Events CSV
            # --------------------------------------------------------

            self._event_file = self._events_path.open(
                mode="w",
                newline="",
                encoding="utf-8",
            )

            self._event_writer = csv.DictWriter(
                self._event_file,
                fieldnames=EVENT_COLUMNS,
                delimiter=config.CSV_DELIMITER,
            )

            self._event_writer.writeheader()

            # --------------------------------------------------------
            # Video timestamp sidecar
            # --------------------------------------------------------

            self._video_timestamps_file = self._video_timestamps_path.open(
                mode="w",
                newline="",
                encoding="utf-8",
            )

            self._video_timestamps_writer = csv.DictWriter(
                self._video_timestamps_file,
                fieldnames=(
                    "frame_index",
                    "timestamp_monotonic_ns",
                    "elapsed_time_s",
                    "timestamp_iso",
                ),
                delimiter=config.CSV_DELIMITER,
            )

            self._video_timestamps_writer.writeheader()

            # --------------------------------------------------------
            # State
            # --------------------------------------------------------

            self._recording = True
            self._samples_since_flush = 0

            # --------------------------------------------------------
            # Metadata
            # --------------------------------------------------------

            self._write_metadata_file()

            # Make headers immediately available on disk.
            self._csv_file.flush()
            self._event_file.flush()

            return self._csv_path

        except Exception:

            # If file creation fails, do not leave TestSession in a
            # false "recording" state.
            self._recording = False

            self._close_files()

            self.session.stop_recording()

            raise

    # =================================================================
    # LOG TIME-SERIES SAMPLE
    # =================================================================

    def log_sample(self) -> None:
        """
        Write one time-series sample.

        MainWindow should call this at approximately 10 Hz while
        recording is active.
        """

        if not self._recording:
            return

        if self._csv_writer is None:
            return

        snapshot = (
            self.session.get_data_snapshot()
        )

        row = {
            column: snapshot.get(column)
            for column in config.CSV_COLUMNS
        }

        self._csv_writer.writerow(
            row
        )

        self._samples_since_flush += 1

        # Approximately once per second at the configured sample rate.
        if (
            self._samples_since_flush
            >= self._flush_every_n_samples
        ):

            if self._csv_file is not None:
                self._csv_file.flush()

            if self._event_file is not None:
                self._event_file.flush()

            self._samples_since_flush = 0

    # =================================================================
    # LOG EVENT
    # =================================================================

    def log_event(
        self,
        event: str,
        details: Any = "",
    ) -> None:
        """
        Write one discrete event.

        Events are only logged while recording is active.

        Parameters
        ----------
        event:
            Short machine-readable event name, for example:

                main_fan_on
                main_fan_pwm_changed
                sensor_1_off
                smoke_machine_on
                sequence_started
                sequence_completed
                stop_all

        details:
            Optional event value or extra information.

            Examples:
                50
                "Step 2"
                {"pwm_percent": 50}

            Dictionaries/lists are JSON encoded.
        """

        if not self._recording:
            return

        if self._event_writer is None:
            return

        event_name = str(
            event
        ).strip()

        if not event_name:
            return

        details_text = self._format_event_details(
            details
        )

        row = {
            "timestamp": datetime.now().strftime(
                config.TIMESTAMP_FORMAT
            ),

            "elapsed_time_s":
                self.session.get_elapsed_time_s(),

            "event":
                event_name,

            "details":
                details_text,
        }

        self._event_writer.writerow(
            row
        )

        # Events are relatively rare and important, so flush each one.
        if self._event_file is not None:
            self._event_file.flush()

    # =================================================================
    # STOP RECORDING
    # =================================================================

    def log_video_frame_timestamp(
        self,
        *,
        frame_index: int,
        timestamp_monotonic_ns: Optional[int] = None,
    ) -> None:
        """Write one row to the video timing sidecar file.

        This creates a common monotonic timeline that can be matched against the
        sensor CSV without relying on MP4 nominal FPS metadata.
        """

        if not self._recording:
            return

        if self._video_timestamps_writer is None:
            return

        if timestamp_monotonic_ns is None:
            timestamp_monotonic_ns = time.monotonic_ns()

        row = {
            "frame_index": int(frame_index),
            "timestamp_monotonic_ns": int(timestamp_monotonic_ns),
            "elapsed_time_s": self.session.get_elapsed_time_s(),
            "timestamp_iso": datetime.now().strftime(config.TIMESTAMP_FORMAT),
        }

        self._video_timestamps_writer.writerow(row)

        if self._video_timestamps_file is not None:
            self._video_timestamps_file.flush()

    def stop(self) -> None:
        """
        Stop recording and close all recording files.

        Calling stop() when no recording is active is harmless.
        """

        if not self._recording:

            self._close_files()
            return

        # Freeze elapsed time before closing files.
        self.session.stop_recording()

        self._recording = False

        # Flush/close all file handles.
        self._close_files()

        # Rewrite metadata so final duration is available.
        #
        # The file paths are intentionally preserved by _close_files().
        self._write_metadata_file()

    # =================================================================
    # RECORDING STATE
    # =================================================================

    def is_recording(self) -> bool:
        """Return whether DataLogger is currently recording."""

        return self._recording

    # =================================================================
    # PATH ACCESS
    # =================================================================

    def get_csv_path(
        self,
    ) -> Optional[Path]:
        """Return path of current/latest time-series CSV."""

        return self._csv_path

    def get_metadata_path(
        self,
    ) -> Optional[Path]:
        """Return path of current/latest metadata JSON."""

        return self._metadata_path

    def get_events_path(
        self,
    ) -> Optional[Path]:
        """Return path of current/latest events CSV."""

        return self._events_path

    def get_video_path(
        self,
    ) -> Optional[Path]:
        """Return path of current/latest associated video file."""

        return self._video_path

    def get_video_2_path(
        self,
    ) -> Optional[Path]:
        """Return path of current/latest secondary camera video file."""

        return self._video_2_path

    def get_video_timestamps_path(
        self,
    ) -> Optional[Path]:
        """Return path of current/latest video timestamp sidecar CSV."""

        return self._video_timestamps_path

    def build_video_path(
        self,
        base_name: Optional[str] = None,
    ) -> Path:
        """Build the companion MP4 path using the same base name as CSV."""

        if base_name is None:
            if self._base_name is not None:
                base_name = self._base_name
            else:
                base_name = self._create_base_filename()

        return (
            self.data_directory
            / f"{base_name}_video{config.VIDEO_FILE_EXTENSION}"
        )

    def build_video_2_path(
        self,
        base_name: Optional[str] = None,
    ) -> Path:
        """Build the companion video path for the secondary camera."""

        if base_name is None:
            if self._base_name is not None:
                base_name = self._base_name
            else:
                base_name = self._create_base_filename()

        return (
            self.data_directory
            / f"{base_name}_video_cam2{config.VIDEO_FILE_EXTENSION}"
        )

    def set_camera_available(
        self,
        available: bool,
    ) -> None:
        """Store the last known camera availability for metadata output."""

        self._camera_available = bool(available)

    def set_camera_metadata(
        self,
        *,
        camera_index: Optional[int] = None,
        camera_auto_exposure: Optional[bool] = None,
        camera_exposure: Optional[int] = None,
        camera_gain: Optional[int] = None,
        video_recorded: Optional[bool] = None,
    ) -> None:
        """Record the currently applied camera configuration for metadata output."""

        if camera_index is not None:
            self._camera_index = int(camera_index)
        if camera_auto_exposure is not None:
            self._camera_auto_exposure = bool(camera_auto_exposure)
        if camera_exposure is not None:
            self._camera_exposure = int(camera_exposure)
        if camera_gain is not None:
            self._camera_gain = int(camera_gain)
        if video_recorded is not None:
            self._video_recorded = bool(video_recorded)

    # =================================================================
    # METADATA
    # =================================================================

    def _write_metadata_file(self) -> None:
        """
        Write experiment metadata JSON.

        This is called both at recording start and recording stop.
        """

        if self._metadata_path is None:
            return

        metadata = (
            self.session.get_metadata().to_dict()
        )

        metadata.update(
            {
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION,

                "sample_rate_hz":
                    config.SENSOR_SAMPLE_RATE_HZ,

                "sample_interval_s":
                    config.SENSOR_SAMPLE_INTERVAL_S,

                "csv_file": (
                    self._csv_path.name
                    if self._csv_path is not None
                    else None
                ),

                "events_file": (
                    self._events_path.name
                    if self._events_path is not None
                    else None
                ),

                "video_file": (
                    self._video_path.name
                    if self._video_path is not None
                    else None
                ),

                "video_2_file": (
                    self._video_2_path.name
                    if self._video_2_path is not None
                    else None
                ),

                "video_timestamps_file": (
                    self._video_timestamps_path.name
                    if self._video_timestamps_path is not None
                    else None
                ),

                "video_recorded":
                    bool(
                        self._video_recorded
                        or (self._video_path is not None and self._video_path.exists())
                    ),

                "camera_index":
                    self._camera_index,

                "camera_auto_exposure":
                    self._camera_auto_exposure,

                "camera_exposure":
                    self._camera_exposure,

                "camera_gain":
                    self._camera_gain,

                "camera_available":
                    bool(self._camera_available),

                "recording_active":
                    self.session.is_recording(),

                "recording_duration_s":
                    self.session.get_elapsed_time_s(),
            }
        )

        with self._metadata_path.open(
            mode="w",
            encoding="utf-8",
        ) as metadata_file:

            json.dump(
                metadata,
                metadata_file,
                indent=4,
                ensure_ascii=False,
            )

    # =================================================================
    # FILENAME
    # =================================================================

    def _create_base_filename(
        self,
    ) -> str:
        """
        Create a readable, unique filename.

        Format is approximately:

            YYYYMMDD_HHMMSS_test-name

        If test name is blank:

            YYYYMMDD_HHMMSS
        """

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        test_name = (
            self.session.get_metadata().test_name
        )

        safe_test_name = self._sanitize_filename_part(
            test_name
        )

        if safe_test_name:

            base_name = (
                f"{timestamp}_{safe_test_name}"
            )

        else:

            base_name = timestamp

        return self._make_unique_base_name(
            base_name
        )

    def _make_unique_base_name(
        self,
        base_name: str,
    ) -> str:
        """
        Avoid accidental overwrite if two recordings start
        within the same second.
        """

        candidate = base_name
        counter = 2

        while self._base_name_exists(
            candidate
        ):

            candidate = (
                f"{base_name}_{counter}"
            )

            counter += 1

        return candidate

    def _base_name_exists(
        self,
        base_name: str,
    ) -> bool:
        """Return True if any recording file already uses this base."""

        csv_path = (
            self.data_directory
            / f"{base_name}{config.CSV_FILE_EXTENSION}"
        )

        metadata_path = (
            self.data_directory
            / f"{base_name}_metadata.json"
        )

        events_path = (
            self.data_directory
            / f"{base_name}_events.csv"
        )

        return (
            csv_path.exists()
            or metadata_path.exists()
            or events_path.exists()
        )

    @staticmethod
    def _sanitize_filename_part(
        value: str,
    ) -> str:
        """
        Convert arbitrary user text into a filesystem-safe filename part.
        """

        value = str(value).strip()

        if not value:
            return ""

        value = re.sub(
            r"[^\w\-]+",
            "_",
            value,
            flags=re.UNICODE,
        )

        value = value.strip(
            "_-"
        )

        return value[:80]

    # =================================================================
    # EVENT DETAILS
    # =================================================================

    @staticmethod
    def _format_event_details(
        details: Any,
    ) -> str:
        """Convert event details to a compact CSV-safe string."""

        if details is None:
            return ""

        if isinstance(
            details,
            (dict, list, tuple),
        ):

            try:
                return json.dumps(
                    details,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )

            except (TypeError, ValueError):
                return str(details)

        return str(details)

    # =================================================================
    # CLOSE FILES
    # =================================================================

    def _close_files(self) -> None:
        """
        Flush and close open CSV/event files.

        File paths are deliberately NOT cleared, so callers can still
        inspect the paths of the latest recording after stop().
        """

        if self._csv_file is not None:

            try:
                self._csv_file.flush()
            finally:
                self._csv_file.close()

        if self._event_file is not None:

            try:
                self._event_file.flush()
            finally:
                self._event_file.close()

        if self._video_timestamps_file is not None:

            try:
                self._video_timestamps_file.flush()
            finally:
                self._video_timestamps_file.close()

        self._csv_file = None
        self._csv_writer = None

        self._event_file = None
        self._event_writer = None

        self._video_timestamps_file = None
        self._video_timestamps_writer = None

        self._samples_since_flush = 0

    # =================================================================
    # CLEANUP
    # =================================================================

    def cleanup(self) -> None:
        """
        Safely stop logging during application shutdown.
        """

        if self._recording:
            self.stop()
        else:
            self._close_files()