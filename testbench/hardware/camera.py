from __future__ import annotations

import math
import sys
import threading
import time
from pathlib import Path
from typing import Iterable, Optional

import config

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


class _CameraWorker(threading.Thread):
    """Dedicated USB-camera acquisition worker.

    The worker is the *only* place that reads frames continuously from
    ``cv2.VideoCapture``.  Recording is also driven from this worker so the
    video frame rate is independent of the application's 10 Hz sensor loop.
    """

    def __init__(
        self,
        capture,
        capture_lock: threading.RLock,
        target_fps: int,
        on_frame,
        on_error,
    ) -> None:
        super().__init__(daemon=True, name="CameraWorker")
        self._capture = capture
        self._capture_lock = capture_lock
        self._target_fps = max(1, int(target_fps))
        self._frame_interval_s = 1.0 / self._target_fps
        self._stop_event = threading.Event()
        self._on_frame = on_frame
        self._on_error = on_error

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        try:
            while not self._stop_event.is_set():
                frame_start = time.monotonic()

                with self._capture_lock:
                    if self._capture is None or not self._capture.isOpened():
                        break
                    ok, frame = self._capture.read()

                if not ok or frame is None:
                    self._on_error("Camera frame read failed")
                    break

                self._on_frame(frame, time.monotonic_ns())

                elapsed = time.monotonic() - frame_start
                sleep_for = self._frame_interval_s - elapsed
                if sleep_for > 0.0:
                    self._stop_event.wait(sleep_for)

        except Exception as exc:  # pragma: no cover - defensive
            self._on_error(str(exc))


class CameraController:
    """Generic OpenCV USB-camera controller for Windows and Raspberry Pi.

    Design rules:
        - Camera acquisition runs in a dedicated worker thread.
        - Full-resolution/raw frames are used for video recording.
        - A separate resized copy is exposed to the GUI for preview.
        - MainWindow must never write preview frames into the video writer.
    """

    SUPPORTED_CAMERA_INDICES = (0,) if sys.platform.startswith("linux") else (0, 1, 2)

    def __init__(
        self,
        camera_index: int = 0,
        preview_size: tuple[int, int] = (640, 360),
        target_fps: int = 30,
    ) -> None:
        self.camera_index = int(camera_index)
        self.preview_size = tuple(preview_size)
        self.target_fps = max(1, int(target_fps))

        self.capture = None
        self._camera_available = False

        self._capture_lock = threading.RLock()
        self._frame_lock = threading.Lock()
        self._recording_lock = threading.RLock()

        self._worker: Optional[_CameraWorker] = None
        self._latest_raw_frame = None
        self._latest_preview_frame = None

        self._recording_writer = None
        self._recording_path: Optional[Path] = None
        self._pending_recording_path: Optional[Path] = None
        self._recording_frame_size: Optional[tuple[int, int]] = None
        self._recording_error: Optional[str] = None
        self._frames_written = 0
        self._video_frame_callback = None

        self._auto_exposure: Optional[bool] = None
        self._exposure: Optional[int] = None
        self._gain: Optional[int] = None

    # ==================================================================
    # CAMERA DISCOVERY / OPENING
    # ==================================================================

    def _candidate_indices(self, preferred: Optional[int] = None) -> Iterable[int]:
        ordered: list[int] = []
        if preferred is not None:
            ordered.append(int(preferred))
        ordered.append(self.camera_index)
        ordered.extend(self.SUPPORTED_CAMERA_INDICES)

        seen: set[int] = set()
        for index in ordered:
            if index not in self.SUPPORTED_CAMERA_INDICES:
                continue
            if index not in seen:
                seen.add(index)
                yield index

    def available_devices(self) -> list[tuple[int, str]]:
        """Return only devices that OpenCV can actually open.

        We intentionally do not add a fake placeholder such as "Camera 0" when
        no real device is detected. The GUI should only show actual hardware
        candidates that were verified by a real probe.
        """

        if cv2 is None:
            return []

        devices: list[tuple[int, str]] = []
        for index in self.SUPPORTED_CAMERA_INDICES:
            cap = None
            try:
                cap = self._open_capture(index)
                if cap is None or not cap.isOpened():
                    continue

                ok, _ = cap.read()
                if not ok:
                    continue

                devices.append((index, f"Camera {index}"))
            except Exception:
                pass
            finally:
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass

        return devices

    def _open_capture(self, index: int):
        if cv2 is None:
            return None

        try:
            if sys.platform == "win32":
                cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            elif sys.platform.startswith("linux"):
                cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
            else:
                cap = cv2.VideoCapture(index, cv2.CAP_ANY)

            if not cap.isOpened():
                try:
                    cap.release()
                except Exception:
                    pass
                cap = cv2.VideoCapture(index, cv2.CAP_ANY)

            return cap
        except Exception:
            return None

    def _configure_capture(self) -> None:
        if self.capture is None or cv2 is None:
            return

        # These are requests, not guarantees. The driver is allowed to select
        # the nearest supported mode.
        with self._capture_lock:
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            self.capture.set(cv2.CAP_PROP_FPS, float(self.target_fps))

    def open(self, camera_index: Optional[int] = None) -> bool:
        """Open the selected camera and start its dedicated worker."""

        if cv2 is None:
            self._camera_available = False
            return False

        preferred = self.camera_index if camera_index is None else int(camera_index)

        if (
            self.capture is not None
            and self.capture.isOpened()
            and preferred == self.camera_index
        ):
            self._camera_available = True
            self._start_worker()
            return True

        self.close()

        for index in self._candidate_indices(preferred):
            cap = self._open_capture(index)
            if cap is None or not cap.isOpened():
                continue

            self.capture = cap
            self.camera_index = index
            self._camera_available = True
            self._configure_capture()
            self.refresh_camera_settings()

            if self._start_worker():
                return True

            try:
                cap.release()
            except Exception:
                pass
            self.capture = None

        self._camera_available = False
        return False

    def set_camera_index(self, camera_index: int) -> bool:
        target_index = int(camera_index)
        if target_index not in self.SUPPORTED_CAMERA_INDICES:
            return False

        if (
            target_index == self.camera_index
            and self.capture is not None
            and self.capture.isOpened()
        ):
            return True

        self.camera_index = target_index
        self.close()
        return self.open(target_index)

    def close(self) -> None:
        self.stop_recording()
        self._stop_worker()

        with self._capture_lock:
            if self.capture is not None:
                try:
                    self.capture.release()
                except Exception:
                    pass
            self.capture = None

        self._camera_available = False
        self._auto_exposure = None
        self._exposure = None
        self._gain = None

        with self._frame_lock:
            self._latest_raw_frame = None
            self._latest_preview_frame = None

    # ==================================================================
    # WORKER
    # ==================================================================

    def _start_worker(self) -> bool:
        if self.capture is None or not self.capture.isOpened():
            return False
        if self._worker is not None and self._worker.is_alive():
            return True

        self._worker = _CameraWorker(
            capture=self.capture,
            capture_lock=self._capture_lock,
            target_fps=self.target_fps,
            on_frame=self._on_frame_ready,
            on_error=self._on_worker_error,
        )
        self._worker.start()
        return True

    def _stop_worker(self) -> None:
        worker = self._worker
        self._worker = None

        if worker is not None:
            worker.stop()
            # Do not wait forever for a broken camera driver.
            worker.join(timeout=2.5)

    def _on_worker_error(self, message: str) -> None:
        self._camera_available = False
        with self._recording_lock:
            self._recording_error = str(message)
        self.stop_recording(preserve_error=True)

    def set_video_frame_callback(self, callback) -> None:
        """Register a callback for each recorded video frame timestamp."""

        self._video_frame_callback = callback

    def _on_frame_ready(self, frame, timestamp_monotonic_ns: Optional[int] = None) -> None:
        if frame is None:
            return

        # GUI data is kept separate from recording data.
        with self._frame_lock:
            self._latest_raw_frame = frame.copy()
            self._latest_preview_frame = self._build_preview_frame(frame)

        # IMPORTANT: only the camera worker writes video frames.
        self._record_raw_frame(frame, timestamp_monotonic_ns)
        self._camera_available = True

    # ==================================================================
    # PREVIEW
    # ==================================================================

    def _build_preview_frame(self, frame):
        if frame is None or cv2 is None:
            return None

        height, width = frame.shape[:2]
        if width <= 0 or height <= 0:
            return frame.copy()

        target_w, target_h = self.preview_size
        scale = min(target_w / width, target_h / height)
        if scale < 1.0:
            new_w = max(1, int(round(width * scale)))
            new_h = max(1, int(round(height * scale)))
            return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        return frame.copy()

    def get_preview_frame(self):
        with self._frame_lock:
            if self._latest_preview_frame is None:
                return None
            return self._latest_preview_frame.copy()

    def read_frame(self):
        """Return a copy of the latest raw frame without reading the device."""
        with self._frame_lock:
            if self._latest_raw_frame is None:
                return None
            return self._latest_raw_frame.copy()

    # ==================================================================
    # CAMERA PROPERTIES
    # ==================================================================

    def _property(self, prop_name: str) -> Optional[float]:
        if self.capture is None or not self.capture.isOpened() or cv2 is None:
            return None

        prop = getattr(cv2, prop_name, None)
        if prop is None:
            return None

        try:
            with self._capture_lock:
                value = float(self.capture.get(prop))
        except Exception:
            return None

        if not math.isfinite(value):
            return None

        # Do NOT reject -1 here. Negative exposure values are normal for many
        # DirectShow webcams.
        return value

    def _set_property(self, prop_name: str, value: float) -> bool:
        if self.capture is None or not self.capture.isOpened() or cv2 is None:
            return False

        prop = getattr(cv2, prop_name, None)
        if prop is None:
            return False

        try:
            with self._capture_lock:
                return bool(self.capture.set(prop, float(value)))
        except Exception:
            return False

    def supports_auto_exposure(self) -> bool:
        return self._property("CAP_PROP_AUTO_EXPOSURE") is not None

    def supports_exposure(self) -> bool:
        return self._property("CAP_PROP_EXPOSURE") is not None

    def supports_gain(self) -> bool:
        return self._property("CAP_PROP_GAIN") is not None

    @staticmethod
    def _interpret_auto_exposure_value(value: float) -> bool:
        """Interpret common DirectShow and V4L2 auto-exposure values."""

        # DirectShow/OpenCV commonly uses 0.25 = manual, 0.75 = auto.
        if abs(value - 0.25) < 0.20:
            return False
        if abs(value - 0.75) < 0.20:
            return True

        # V4L2 commonly uses 1 = manual and 3 = aperture-priority auto.
        if abs(value - 1.0) < 0.20:
            return False
        if value >= 2.0:
            return True

        if value <= 0.0:
            return False
        return bool(value)

    def get_auto_exposure(self) -> Optional[bool]:
        value = self._property("CAP_PROP_AUTO_EXPOSURE")
        if value is None:
            return None
        return self._interpret_auto_exposure_value(value)

    def set_auto_exposure(self, enabled: bool) -> bool:
        if not self.supports_auto_exposure():
            return False

        enabled = bool(enabled)

        if sys.platform == "win32":
            candidates = (0.75, 1.0) if enabled else (0.25, 0.0)
        elif sys.platform.startswith("linux"):
            candidates = (3.0, 0.75) if enabled else (1.0, 0.25)
        else:
            candidates = (0.75, 1.0, 3.0) if enabled else (0.25, 0.0, 1.0)

        for candidate in candidates:
            if not self._set_property("CAP_PROP_AUTO_EXPOSURE", candidate):
                continue

            # Some drivers update property state asynchronously.
            time.sleep(0.03)
            actual = self.get_auto_exposure()
            if actual is None:
                continue
            if actual == enabled:
                self._auto_exposure = actual
                return True

        # Read back final state even if the requested state was rejected.
        self._auto_exposure = self.get_auto_exposure()
        return self._auto_exposure == enabled

    def get_exposure(self) -> Optional[int]:
        value = self._property("CAP_PROP_EXPOSURE")
        if value is None:
            return None
        return int(round(value))

    def set_exposure(self, value: int) -> bool:
        if not self.supports_exposure():
            return False

        try:
            target = int(value)
        except Exception:
            return False

        if not self._set_property("CAP_PROP_EXPOSURE", float(target)):
            return False

        time.sleep(0.02)
        actual = self.get_exposure()
        self._exposure = actual
        return actual is not None

    def get_gain(self) -> Optional[int]:
        value = self._property("CAP_PROP_GAIN")
        if value is None:
            return None
        return int(round(value))

    def set_gain(self, value: int) -> bool:
        if not self.supports_gain():
            return False

        try:
            target = int(value)
        except Exception:
            return False

        if not self._set_property("CAP_PROP_GAIN", float(target)):
            return False

        time.sleep(0.02)
        actual = self.get_gain()
        self._gain = actual
        return actual is not None

    def refresh_camera_settings(self) -> None:
        if not self.is_open():
            self._auto_exposure = None
            self._exposure = None
            self._gain = None
            return

        self._auto_exposure = self.get_auto_exposure()
        self._exposure = self.get_exposure()
        self._gain = self.get_gain()

    # ==================================================================
    # STATE
    # ==================================================================

    def is_available(self) -> bool:
        return bool(
            cv2 is not None
            and self.capture is not None
            and self.capture.isOpened()
            and self._camera_available
        )

    def is_open(self) -> bool:
        return bool(self.capture is not None and self.capture.isOpened())

    # ==================================================================
    # VIDEO RECORDING
    # ==================================================================

    def start_recording(self, video_path: str | Path) -> bool:
        """Arm recording; the worker opens the writer on the next raw frame."""

        if cv2 is None or not self.is_open():
            return False
        if self._worker is None or not self._worker.is_alive():
            return False

        with self._recording_lock:
            if self._recording_writer is not None and self._recording_writer.isOpened():
                return True

            self._recording_error = None
            self._frames_written = 0
            self._pending_recording_path = Path(video_path)
            self._recording_path = Path(video_path)
            self._recording_frame_size = None

        return True

    def _resolve_recording_profile(self, width: int, height: int) -> tuple[int, int, int]:
        """Return a lightweight recording size/FPS profile to avoid long encoding stalls."""

        target_width, target_height = getattr(
            config,
            "DEFAULT_CAMERA_RECORD_RESOLUTION",
            (1280, 720),
        )
        record_fps = getattr(
            config,
            "DEFAULT_CAMERA_RECORD_FPS",
            15,
        )

        max_width = max(1, int(target_width))
        max_height = max(1, int(target_height))

        width = max(1, int(width))
        height = max(1, int(height))

        scale = min(max_width / width, max_height / height, 1.0)
        output_width = max(1, int(round(width * scale)))
        output_height = max(1, int(round(height * scale)))

        fps = max(1, min(int(record_fps), int(self.target_fps)))
        return output_width, output_height, fps

    @staticmethod
    def _video_codec_for_path(path: str | Path) -> str:
        """Use a codec that matches the output container to avoid CPU-heavy MJPG->MP4 fallback."""

        suffix = str(path).lower()
        if suffix.endswith(".avi"):
            return "MJPG"
        return "mp4v"

    def _open_recording_writer_locked(self, frame) -> bool:
        """Open a writer using a container-safe codec profile."""

        if cv2 is None or frame is None or self._pending_recording_path is None:
            return False

        path = Path(self._pending_recording_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if frame.ndim != 3 or frame.shape[2] != 3:
            self._recording_error = "Camera frame is not 3-channel BGR"
            self._pending_recording_path = None
            return False

        height, width = frame.shape[:2]
        if width <= 0 or height <= 0:
            self._recording_error = "Invalid camera frame size"
            self._pending_recording_path = None
            return False

        output_width, output_height, fps = self._resolve_recording_profile(width, height)
        preferred_codec = self._video_codec_for_path(path)
        fallback_codec = "MJPG" if preferred_codec == "mp4v" else "mp4v"

        writer = None
        for codec in (preferred_codec, fallback_codec):
            writer = cv2.VideoWriter(
                str(path),
                cv2.VideoWriter_fourcc(*codec),
                float(fps),
                (int(output_width), int(output_height)),
                True,
            )
            if writer.isOpened():
                break
            try:
                writer.release()
            except Exception:
                pass
            writer = None

        if writer is None or not writer.isOpened():
            self._recording_error = "Could not open VideoWriter using a safe codec profile"
            self._pending_recording_path = None
            return False

        self._recording_writer = writer
        self._recording_frame_size = (int(output_width), int(output_height))
        self._pending_recording_path = None
        return True

    def _record_raw_frame(self, frame, timestamp_monotonic_ns: Optional[int] = None) -> None:
        """Write exactly one raw frame per worker capture cycle."""

        if cv2 is None or frame is None:
            return

        with self._recording_lock:
            if self._pending_recording_path is not None and self._recording_writer is None:
                if not self._open_recording_writer_locked(frame):
                    return

            writer = self._recording_writer
            if writer is None or not writer.isOpened():
                return

            try:
                output = frame
                expected = self._recording_frame_size
                actual_size = (int(frame.shape[1]), int(frame.shape[0]))

                # A VideoWriter requires every frame to have exactly the same
                # dimensions.  Normally the capture size is constant, but this
                # guard prevents corrupt files if a driver changes mode.
                if expected is not None and actual_size != expected:
                    output = cv2.resize(frame, expected, interpolation=cv2.INTER_AREA)

                if not output.flags["C_CONTIGUOUS"]:
                    output = output.copy()

                writer.write(output)
                self._frames_written += 1

                if self._video_frame_callback is not None:
                    self._video_frame_callback(
                        frame_index=self._frames_written,
                        timestamp_monotonic_ns=timestamp_monotonic_ns,
                    )

            except Exception as exc:
                self._recording_error = f"Video write failed: {exc}"
                try:
                    writer.release()
                except Exception:
                    pass
                self._recording_writer = None
                self._pending_recording_path = None

    def stop_recording(self, preserve_error: bool = False) -> None:
        with self._recording_lock:
            if self._recording_writer is not None:
                try:
                    self._recording_writer.release()
                except Exception:
                    pass

            self._recording_writer = None
            self._pending_recording_path = None
            self._recording_frame_size = None

            if not preserve_error:
                self._recording_error = None

    def is_recording(self) -> bool:
        with self._recording_lock:
            return bool(
                (self._recording_writer is not None and self._recording_writer.isOpened())
                or self._pending_recording_path is not None
            )

    def get_recording_path(self) -> Optional[Path]:
        return self._recording_path

    def get_recording_error(self) -> Optional[str]:
        with self._recording_lock:
            return self._recording_error

    def get_frames_written(self) -> int:
        with self._recording_lock:
            return int(self._frames_written)

    def write_frame(self, frame) -> bool:
        """Deprecated compatibility method.

        Recording is worker-owned.  Keeping this method as a no-op prevents
        older callers from accidentally writing resized preview frames into the
        full-resolution video file.
        """
        return False
