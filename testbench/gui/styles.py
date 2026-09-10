"""
Central styling for the Airflow Smoke Test Bench GUI.

This module contains presentation only.
It must not contain hardware, recording, sequence, or application logic.

The rest of the GUI can import:
    from gui.styles import APP_STYLESHEET

and apply it to QApplication:
    app.setStyleSheet(APP_STYLESHEET)

The stylesheet is designed around the approved dark dashboard mockups for:
    - CONTROL
    - LIVE DATA
    - SEQUENCE
"""

# =============================================================================
# COLOUR PALETTE
# =============================================================================

# Main backgrounds
BACKGROUND = "#07131F"
BACKGROUND_SECONDARY = "#0A1825"

# Cards / panels
CARD = "#0D1D2B"
CARD_ALT = "#102332"
CARD_DARK = "#091722"

# Borders
BORDER = "#243A4D"
BORDER_LIGHT = "#31506A"

# Text
TEXT_PRIMARY = "#F2F6FA"
TEXT_SECONDARY = "#B8C5D1"
TEXT_MUTED = "#7F91A3"
TEXT_DISABLED = "#566675"

# Accent
BLUE = "#1597FF"
BLUE_HOVER = "#32A7FF"
BLUE_PRESSED = "#087ACF"
BLUE_DARK = "#0B5790"

# State colours
GREEN = "#20E67A"
GREEN_DARK = "#0C8C49"

RED = "#FF344D"
RED_HOVER = "#FF5065"
RED_DARK = "#7A1725"

ORANGE = "#FF7A21"

# Neutral state
OFF = "#8293A4"
OFF_DARK = "#3B4E60"


# =============================================================================
# MAIN APPLICATION STYLESHEET
# =============================================================================

APP_STYLESHEET = f"""

/* ==========================================================================
   GLOBAL
   ========================================================================== */

QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {BACKGROUND};
}}

QDialog {{
    background-color: {BACKGROUND};
    color: {TEXT_PRIMARY};
}}


/* ==========================================================================
   LABELS
   ========================================================================== */

QLabel {{
    background: transparent;
    color: {TEXT_PRIMARY};
}}

QLabel[role="title"] {{
    font-size: 23px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}

QLabel[role="subtitle"] {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
}}

QLabel[role="cardTitle"] {{
    font-size: 16px;
    font-weight: 650;
    color: {TEXT_PRIMARY};
}}

QLabel[role="sectionTitle"] {{
    font-size: 18px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}

QLabel[role="fieldLabel"] {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

QLabel[role="muted"] {{
    color: {TEXT_MUTED};
}}

QLabel[role="liveValue"] {{
    font-size: 26px;
    font-weight: 700;
    color: {GREEN};
}}

QLabel[role="liveValueSensor1"] {{
    font-size: 26px;
    font-weight: 700;
    color: {BLUE};
}}

QLabel[role="liveValueSensor2"] {{
    font-size: 26px;
    font-weight: 700;
    color: {ORANGE};
}}

QLabel[role="timer"] {{
    font-size: 24px;
    font-weight: 650;
    color: {TEXT_PRIMARY};
}}

QLabel[role="statusOn"] {{
    color: {GREEN};
    font-weight: 600;
}}

QLabel[role="statusOff"] {{
    color: {TEXT_MUTED};
}}

QLabel[role="statusRecording"] {{
    color: {RED};
    font-weight: 700;
}}

QLabel[role="statusReady"] {{
    color: {GREEN};
    font-weight: 600;
}}


/* ==========================================================================
   CARDS

   Use:
       widget.setProperty("card", True)

   ========================================================================== */

QFrame[card="true"],
QWidget[card="true"] {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 9px;
}}

QFrame[card="secondary"],
QWidget[card="secondary"] {{
    background-color: {CARD_ALT};
    border: 1px solid {BORDER};
    border-radius: 9px;
}}

QFrame[card="dark"],
QWidget[card="dark"] {{
    background-color: {CARD_DARK};
    border: 1px solid {BORDER};
    border-radius: 7px;
}}


/* ==========================================================================
   GROUP BOXES

   Existing widgets can still use QGroupBox while we gradually migrate
   the interface to cards.
   ========================================================================== */

QGroupBox {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 9px;
    margin-top: 13px;
    padding-top: 13px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 13px;
    padding: 0 6px;
    color: {TEXT_PRIMARY};
    background-color: {CARD};
}}


/* ==========================================================================
   TEXT INPUTS
   ========================================================================== */

QLineEdit,
QTextEdit,
QPlainTextEdit {{
    background-color: {BACKGROUND_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 9px;
    selection-background-color: {BLUE};
    selection-color: white;
}}

QLineEdit:hover,
QTextEdit:hover,
QPlainTextEdit:hover {{
    border: 1px solid {BORDER_LIGHT};
}}

QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus {{
    border: 1px solid {BLUE};
}}

QLineEdit:disabled,
QTextEdit:disabled,
QPlainTextEdit:disabled {{
    background-color: {CARD_DARK};
    color: {TEXT_DISABLED};
    border-color: {BORDER};
}}


/* ==========================================================================
   STANDARD BUTTONS
   ========================================================================== */

QPushButton {{
    background-color: {CARD_ALT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 14px;
    min-height: 22px;
}}

QPushButton:hover {{
    background-color: {BORDER};
    border-color: {BORDER_LIGHT};
}}

QPushButton:pressed {{
    background-color: {CARD_DARK};
}}

QPushButton:disabled {{
    background-color: {CARD_DARK};
    color: {TEXT_DISABLED};
    border-color: {BORDER};
}}


/* ==========================================================================
   PRIMARY BUTTON

   Use:
       button.setProperty("role", "primary")
   ========================================================================== */

QPushButton[role="primary"] {{
    background-color: {BLUE};
    color: white;
    border: 1px solid {BLUE};
    font-weight: 650;
}}

QPushButton[role="primary"]:hover {{
    background-color: {BLUE_HOVER};
    border-color: {BLUE_HOVER};
}}

QPushButton[role="primary"]:pressed {{
    background-color: {BLUE_PRESSED};
}}


/* ==========================================================================
   RUN SEQUENCE BUTTON
   ========================================================================== */

QPushButton[role="run"] {{
    background-color: {GREEN};
    color: #04130B;
    border: 1px solid {GREEN};
    border-radius: 7px;
    font-size: 14px;
    font-weight: 700;
    min-height: 36px;
}}

QPushButton[role="run"]:hover {{
    background-color: #43EF91;
}}

QPushButton[role="run"]:pressed {{
    background-color: {GREEN_DARK};
    color: white;
}}

QPushButton[role="run"]:disabled {{
    background-color: {OFF_DARK};
    color: {TEXT_DISABLED};
    border-color: {BORDER};
}}


/* ==========================================================================
   STOP SEQUENCE BUTTON
   ========================================================================== */

QPushButton[role="stopSequence"] {{
    background-color: {CARD_ALT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 7px;
    font-weight: 600;
    min-height: 36px;
}}

QPushButton[role="stopSequence"]:hover {{
    border-color: {RED};
    color: {RED};
}}

QPushButton[role="stopSequence"]:disabled {{
    background-color: {CARD_DARK};
    color: {TEXT_DISABLED};
    border-color: {BORDER};
}}


/* ==========================================================================
   STOP ALL

   Deliberately visually dominant.
   ========================================================================== */

QPushButton[role="stopAll"] {{
    background-color: {RED_DARK};
    color: white;
    border: 2px solid {RED};
    border-radius: 9px;
    font-size: 20px;
    font-weight: 800;
    min-height: 64px;
}}

QPushButton[role="stopAll"]:hover {{
    background-color: {RED};
    color: white;
}}

QPushButton[role="stopAll"]:pressed {{
    background-color: #B8142B;
    border-color: white;
}}


/* ==========================================================================
   RECORDING BUTTONS
   ========================================================================== */

QPushButton[role="record"] {{
    background-color: {CARD_ALT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 7px;
    font-weight: 650;
}}

QPushButton[role="record"]:hover {{
    border-color: {RED};
}}

QPushButton[role="recording"] {{
    background-color: {RED_DARK};
    color: white;
    border: 1px solid {RED};
    border-radius: 7px;
    font-weight: 700;
}}


/* ==========================================================================
   ON / OFF TOGGLE BUTTONS

   Existing QPushButton checkable controls can use:
       button.setCheckable(True)
       button.setProperty("role", "toggle")

   Checked = ON
   Unchecked = OFF
   ========================================================================== */

QPushButton[role="toggle"] {{
    background-color: {OFF_DARK};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 14px;
    min-width: 58px;
    min-height: 28px;
    padding: 0 10px;
    font-weight: 700;
}}

QPushButton[role="toggle"]:hover {{
    border-color: {BORDER_LIGHT};
}}

QPushButton[role="toggle"]:checked {{
    background-color: {GREEN};
    color: #04130B;
    border-color: {GREEN};
}}

QPushButton[role="toggle"]:checked:hover {{
    background-color: #43EF91;
}}


/* ==========================================================================
   CHECKBOXES
   ========================================================================== */

QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {BORDER_LIGHT};
    border-radius: 4px;
    background-color: {BACKGROUND_SECONDARY};
}}

QCheckBox::indicator:hover {{
    border-color: {BLUE};
}}

QCheckBox::indicator:checked {{
    background-color: {BLUE};
    border-color: {BLUE};
}}

QCheckBox:disabled {{
    color: {TEXT_DISABLED};
}}


/* ==========================================================================
   COMBO BOXES
   ========================================================================== */

QComboBox {{
    background-color: {BACKGROUND_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 28px 6px 9px;
    min-height: 22px;
}}

QComboBox:hover {{
    border-color: {BORDER_LIGHT};
}}

QComboBox:focus {{
    border-color: {BLUE};
}}

QComboBox:disabled {{
    background-color: {CARD_DARK};
    color: {TEXT_DISABLED};
}}

QComboBox QAbstractItemView {{
    background-color: {CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    selection-background-color: {BLUE_DARK};
    selection-color: white;
    outline: none;
}}


/* ==========================================================================
   SPIN BOXES
   ========================================================================== */

QSpinBox,
QDoubleSpinBox {{
    background-color: {BACKGROUND_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 23px;
}}

QSpinBox:hover,
QDoubleSpinBox:hover {{
    border-color: {BORDER_LIGHT};
}}

QSpinBox:focus,
QDoubleSpinBox:focus {{
    border-color: {BLUE};
}}

QSpinBox:disabled,
QDoubleSpinBox:disabled {{
    background-color: {CARD_DARK};
    color: {TEXT_DISABLED};
}}


/* ==========================================================================
   SLIDERS

   Available for the fan PWM cards if we decide to use a slider visually.
   The underlying PWM functionality remains unchanged.
   ========================================================================== */

QSlider::groove:horizontal {{
    height: 6px;
    background-color: {OFF_DARK};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background-color: {BLUE};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background-color: {BLUE};
    border: none;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {BLUE_HOVER};
}}

QSlider:disabled {{
    opacity: 0.45;
}}


/* ==========================================================================
   TAB BAR
   ========================================================================== */

QTabWidget::pane {{
    border: none;
    background-color: {BACKGROUND};
}}

QTabBar {{
    background-color: transparent;
}}

QTabBar::tab {{
    background-color: {BACKGROUND_SECONDARY};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    padding: 10px 24px;
    min-width: 105px;
    min-height: 25px;
}}

QTabBar::tab:first {{
    border-top-left-radius: 7px;
    border-bottom-left-radius: 7px;
}}

QTabBar::tab:last {{
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
}}

QTabBar::tab:selected {{
    background-color: {BLUE_DARK};
    color: white;
    border: 1px solid {BLUE};
    font-weight: 650;
}}

QTabBar::tab:hover:!selected {{
    background-color: {CARD_ALT};
    color: {TEXT_PRIMARY};
}}


/* ==========================================================================
   TABLES - SEQUENCE
   ========================================================================== */

QTableWidget,
QTableView {{
    background-color: {CARD_DARK};
    alternate-background-color: {CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 7px;
    gridline-color: {BORDER};
    selection-background-color: {BLUE_DARK};
    selection-color: white;
}}

QTableWidget::item,
QTableView::item {{
    padding: 6px;
    border: none;
}}

QTableWidget::item:selected,
QTableView::item:selected {{
    background-color: {BLUE_DARK};
}}

QHeaderView::section {{
    background-color: {CARD_ALT};
    color: {TEXT_SECONDARY};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    padding: 8px;
    font-weight: 600;
}}


/* ==========================================================================
   SCROLL BARS
   ========================================================================== */

QScrollBar:vertical {{
    background-color: {BACKGROUND_SECONDARY};
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {OFF_DARK};
    min-height: 25px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {BORDER_LIGHT};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {BACKGROUND_SECONDARY};
    height: 10px;
}}

QScrollBar::handle:horizontal {{
    background-color: {OFF_DARK};
    min-width: 25px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {BORDER_LIGHT};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
}}


/* ==========================================================================
   SPLITTER
   ========================================================================== */

QSplitter::handle {{
    background-color: {BACKGROUND};
}}

QSplitter::handle:horizontal {{
    width: 6px;
}}

QSplitter::handle:vertical {{
    height: 6px;
}}

QSplitter::handle:hover {{
    background-color: {BORDER};
}}


/* ==========================================================================
   TOOLTIPS
   ========================================================================== */

QToolTip {{
    background-color: {CARD_ALT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_LIGHT};
    padding: 6px;
}}


/* ==========================================================================
   STATUS BAR
   ========================================================================== */

QStatusBar {{
    background-color: {BACKGROUND};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER};
}}

QStatusBar::item {{
    border: none;
}}

"""


# =============================================================================
# PYQTGRAPH SETTINGS
# =============================================================================

# These constants will be used later by live_tab.py and live_status_panel.py.
# Keeping them here ensures that all plots use the same visual language.

PLOT_BACKGROUND = "#07131F"
PLOT_FOREGROUND = "#B8C5D1"

PLOT_GRID_ALPHA = 0.18

SENSOR_1_COLOR = "#1597FF"
SENSOR_2_COLOR = "#FF7A21"

SEQUENCE_MARKER_COLOR = "#8DA8BF"

PLOT_LINE_WIDTH = 2
MINI_PLOT_LINE_WIDTH = 1.5


# =============================================================================
# LAYOUT CONSTANTS
# =============================================================================

# General spacing used by the redesigned tabs.
PAGE_MARGIN = 16
CARD_MARGIN = 12
CARD_SPACING = 12

# Main CONTROL / SEQUENCE layout:
# approximately 2/3 controls and 1/3 live status.
MAIN_CONTENT_STRETCH = 2
SIDE_PANEL_STRETCH = 1

# Common card radius. Primarily documentation/reference because Qt's
# stylesheet above contains the actual value.
CARD_RADIUS = 9


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def repolish(widget) -> None:
    """
    Force Qt to re-evaluate stylesheet properties for a widget.

    Useful after changing dynamic properties such as:

        widget.setProperty("role", "toggle")
        widget.setProperty("card", True)

    or when a state-dependent style needs to be refreshed.
    """
    style = widget.style()

    if style is None:
        return

    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def set_role(widget, role: str) -> None:
    """
    Assign a stylesheet role to a widget and immediately refresh its style.

    Example:
        set_role(start_button, "primary")
        set_role(stop_all_button, "stopAll")
        set_role(sensor_button, "toggle")
    """
    widget.setProperty("role", role)
    repolish(widget)


def set_card(widget, variant=True) -> None:
    """
    Style a QFrame/QWidget as a dashboard card.

    Examples:
        set_card(frame)
        set_card(frame, "secondary")
        set_card(frame, "dark")
    """
    widget.setProperty("card", variant)
    repolish(widget)


def set_label_role(label, role: str) -> None:
    """
    Apply one of the predefined label roles.

    Example:
        set_label_role(title_label, "cardTitle")
        set_label_role(voltage_label, "liveValue")
        set_label_role(status_label, "statusRecording")
    """
    label.setProperty("role", role)
    repolish(label)