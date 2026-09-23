import json
import os
import tempfile
import unittest

from PySide6.QtWidgets import QApplication

from gui.control_tab import ControlTab
from gui.live_tab import LiveTab
from hardware.camera import CameraController
from services.logger import DataLogger
from services.test_session import TestSession


class CameraLoggingTest(unittest.TestCase):
    def test_video_filename_uses_same_base_name_as_csv(self):
        session = TestSession()
        session.set_metadata(test_name="Test 01")

        with tempfile.TemporaryDirectory() as temp_dir:
            logger = DataLogger(session=session, data_directory=temp_dir)
            base_name = logger._create_base_filename()

            video_path = logger.build_video_path(base_name=base_name)

            self.assertTrue(video_path.name.endswith("_video.mp4"))
            self.assertEqual(video_path.name, f"{base_name}_video.mp4")
            self.assertFalse(video_path.name.startswith("video_"))

    def test_camera_source_selection_is_stored_and_enumerated(self):
        camera = CameraController(camera_index=0)

        devices = camera.available_devices()
        self.assertIsInstance(devices, list)

        if devices:
            camera.set_camera_index(devices[0][0])
            self.assertEqual(camera.camera_index, devices[0][0])
        else:
            camera.set_camera_index(0)
            self.assertEqual(camera.camera_index, 0)

    def test_live_tab_camera_preview_off_is_safe(self):
        app = QApplication.instance() or QApplication([])
        live_tab = LiveTab()

        live_tab.set_camera_preview(None, False)
        live_tab.set_camera_preview(None, True)

        self.assertEqual(live_tab.camera_preview_label.text(), "CAMERA OFF")

    def test_camera_settings_metadata_are_written(self):
        session = TestSession()
        session.set_metadata(test_name="Test 02")

        with tempfile.TemporaryDirectory() as temp_dir:
            logger = DataLogger(session=session, data_directory=temp_dir)
            logger.start()
            logger.set_camera_metadata(
                camera_index=1,
                camera_auto_exposure=True,
                camera_exposure=150,
                camera_gain=80,
                video_recorded=True,
            )
            logger.stop()

            with open(logger.get_metadata_path(), "r", encoding="utf-8") as metadata_file:
                payload = json.load(metadata_file)

            self.assertEqual(payload["camera_index"], 1)
            self.assertTrue(payload["camera_auto_exposure"])
            self.assertEqual(payload["camera_exposure"], 150)
            self.assertEqual(payload["camera_gain"], 80)
            self.assertTrue(payload["video_recorded"])

    def test_camera_auto_exposure_defaults_to_on(self):
        camera = CameraController(camera_index=0)
        self.assertTrue(camera.get_auto_exposure() in (True, None))

    def test_recording_profile_is_capped_for_fast_video_writes(self):
        camera = CameraController(camera_index=0)
        capture_size = (1920, 1080)

        width, height, fps = camera._resolve_recording_profile(capture_size[0], capture_size[1])

        self.assertEqual((width, height), (1280, 720))
        self.assertLessEqual(fps, 15)

    def test_camera_source_dropdown_only_lists_real_devices(self):
        app = QApplication.instance() or QApplication([])
        control_tab = ControlTab()

        control_tab.set_camera_source_options([])

        self.assertEqual(control_tab.camera_source_combo.count(), 0)
        self.assertFalse(control_tab.camera_source_combo.isEnabled())

    def test_video_codec_matches_container(self):
        camera = CameraController(camera_index=0)

        self.assertEqual(camera._video_codec_for_path("recording.mp4"), "mp4v")
        self.assertEqual(camera._video_codec_for_path("recording.avi"), "MJPG")

    def test_logger_creates_video_sync_sidecar_on_start(self):
        session = TestSession()
        session.set_metadata(test_name="Sync Test")

        with tempfile.TemporaryDirectory() as temp_dir:
            logger = DataLogger(session=session, data_directory=temp_dir)
            logger.start()

            self.assertIsNotNone(logger.get_video_timestamps_path())
            self.assertTrue(logger.get_video_timestamps_path().name.endswith("_video_timestamps.csv"))

            logger.log_video_frame_timestamp(frame_index=1, timestamp_monotonic_ns=123456789)

            logger.stop()

            with open(logger.get_video_timestamps_path(), "r", encoding="utf-8") as video_timestamps_file:
                rows = video_timestamps_file.read().strip().splitlines()

            self.assertGreaterEqual(len(rows), 2)
            self.assertIn("frame_index", rows[0])
            self.assertIn("1", rows[1])


if __name__ == "__main__":
    unittest.main()
