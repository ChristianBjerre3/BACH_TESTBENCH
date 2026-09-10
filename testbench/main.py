"""
main.py

Entry point for the airflow/smoke test bench application.

This module starts the Qt application and creates the MainWindow.

The actual application logic is located in:
    - hardware/
    - services/
    - gui/

Run the application from the project root with:

    python main.py
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

import config
from gui.main_window import MainWindow


def main() -> int:
    """
    Start the airflow/smoke test bench application.

    Returns
    -------
    int
        Qt application exit code.
    """

    # ------------------------------------------------------------
    # Create Qt application
    # ------------------------------------------------------------

    app = QApplication(sys.argv)

    app.setApplicationName(
        config.APP_NAME
    )

    app.setApplicationVersion(
        config.APP_VERSION
    )

    # ------------------------------------------------------------
    # Create main window
    # ------------------------------------------------------------

    window = None

    try:
        window = MainWindow()
        window.show()

        # --------------------------------------------------------
        # Start Qt event loop
        # --------------------------------------------------------

        exit_code = app.exec()

        return exit_code

    except Exception as exc:
        print(
            f"Fatal application error: {exc}",
            file=sys.stderr,
        )

        return 1

    finally:
        # --------------------------------------------------------
        # Final safety cleanup
        # --------------------------------------------------------

        if window is not None:
            try:
                window.cleanup()
            except Exception as cleanup_error:
                print(
                    f"Cleanup error: {cleanup_error}",
                    file=sys.stderr,
                )


if __name__ == "__main__":
    sys.exit(main())