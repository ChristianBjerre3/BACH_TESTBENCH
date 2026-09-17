from __future__ import annotations

from hardware.camera import CameraController


class CameraController(CameraController):
    """Simulation-side camera shim.

    The project is currently running in simulation mode on Windows, but
    the USB camera logic itself is intentionally OpenCV-based and can be
    used with real webcams during desktop testing.
    """

    pass
