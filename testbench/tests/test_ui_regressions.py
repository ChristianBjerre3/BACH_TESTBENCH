import unittest

from PySide6.QtWidgets import QApplication

import config
from gui.control_tab import ControlTab
from gui.live_tab import LiveTab
from gui.sequence_tab import SequenceTab


class UiRegressionTests(unittest.TestCase):
    def test_control_pwm_controls_are_numeric_and_range_0_to_100(self):
        app = QApplication.instance() or QApplication([])
        tab = ControlTab()

        self.assertEqual(tab.main_fan_pwm_combo.minimum(), 0)
        self.assertEqual(tab.main_fan_pwm_combo.maximum(), 100)
        self.assertEqual(tab.smoke_fan_pwm_combo.minimum(), 0)
        self.assertEqual(tab.smoke_fan_pwm_combo.maximum(), 100)

    def test_live_sensor_plot_has_fixed_voltage_axis_0_to_2_6(self):
        app = QApplication.instance() or QApplication([])
        tab = LiveTab()

        y_min, y_max = tab.plot.getAxis("left").range
        self.assertAlmostEqual(y_min, 0.0)
        self.assertAlmostEqual(y_max, 2.6)

    def test_live_tab_has_future_proof_camera_preview_slots(self):
        app = QApplication.instance() or QApplication([])
        tab = LiveTab()

        self.assertTrue(hasattr(tab, "camera_preview_label"))
        self.assertTrue(hasattr(tab, "camera_preview_label_2"))
        self.assertTrue(hasattr(tab, "set_secondary_camera_preview"))
        self.assertEqual(tab.camera_preview_label_2.text(), "CAMERA 2\nREADY")

    def test_control_tab_has_camera_2_controls_like_camera_1(self):
        app = QApplication.instance() or QApplication([])
        tab = ControlTab()

        self.assertTrue(hasattr(tab, "camera_2_button"))
        self.assertTrue(hasattr(tab, "camera_2_source_combo"))
        self.assertTrue(hasattr(tab, "camera_2_auto_exposure_checkbox"))
        self.assertTrue(hasattr(tab, "camera_2_exposure_spin"))
        self.assertTrue(hasattr(tab, "camera_2_gain_spin"))
        self.assertTrue(hasattr(tab, "camera_2_record_video_checkbox"))
        self.assertTrue(hasattr(tab, "camera_2_status_label"))

    def test_main_window_initializes_secondary_camera_state(self):
        app = QApplication.instance() or QApplication([])
        from gui.main_window import MainWindow

        previous_mode = config.HARDWARE_MODE
        config.HARDWARE_MODE = "simulation"
        try:
            window = MainWindow()
        finally:
            config.HARDWARE_MODE = previous_mode

        self.assertTrue(hasattr(window, "_camera_2_enabled"))
        self.assertFalse(window._camera_2_enabled)
        self.assertTrue(hasattr(window, "_camera_2_record_video"))
        self.assertFalse(window._camera_2_record_video)

    def test_camera_cards_are_split_into_two_independent_cards(self):
        app = QApplication.instance() or QApplication([])
        tab = ControlTab()

        self.assertTrue(hasattr(tab, "camera_1_card"))
        self.assertTrue(hasattr(tab, "camera_2_card"))
        self.assertIsNotNone(tab.camera_1_card)
        self.assertIsNotNone(tab.camera_2_card)

        self.assertIsNotNone(tab.camera_1_card)
        self.assertIsNotNone(tab.camera_2_card)

        dashboard_layout = tab.layout().itemAt(1).layout()
        row_3_col_0 = dashboard_layout.itemAtPosition(3, 0)
        row_3_col_1 = dashboard_layout.itemAtPosition(3, 1)

        self.assertIsNotNone(row_3_col_0)
        self.assertIsNotNone(row_3_col_1)
        self.assertEqual(row_3_col_0.widget(), tab.camera_1_card)
        self.assertEqual(row_3_col_1.widget(), tab.camera_2_card)

    def test_sequence_new_step_defaults_to_5_seconds_and_copies_previous_step(self):
        app = QApplication.instance() or QApplication([])
        tab = SequenceTab()
        tab.clear_steps()

        tab.add_step(duration_s=5.0, main_fan_active=True, main_fan_pwm_percent=50, smoke_fan_active=True, smoke_fan_pwm_percent=25)
        tab.add_step()

        duration_widget = tab.sequence_table.cellWidget(1, 0)
        main_fan_widget = tab.sequence_table.cellWidget(1, 1)
        main_pwm_widget = tab.sequence_table.cellWidget(1, 2)
        smoke_fan_widget = tab.sequence_table.cellWidget(1, 3)
        smoke_pwm_widget = tab.sequence_table.cellWidget(1, 4)

        self.assertAlmostEqual(float(duration_widget.value()), 5.0)
        self.assertEqual(bool(main_fan_widget.currentData()), True)
        self.assertEqual(int(main_pwm_widget.value()), 50)
        self.assertEqual(bool(smoke_fan_widget.currentData()), True)
        self.assertEqual(int(smoke_pwm_widget.value()), 25)

    def test_stop_step_is_one_second_all_off_zero_pwm(self):
        app = QApplication.instance() or QApplication([])
        tab = SequenceTab()
        tab.clear_steps()

        tab.add_step(duration_s=5.0, main_fan_active=True, main_fan_pwm_percent=50, smoke_fan_active=True, smoke_fan_pwm_percent=25)
        tab.add_stop_step()

        duration_widget = tab.sequence_table.cellWidget(1, 0)
        main_fan_widget = tab.sequence_table.cellWidget(1, 1)
        main_pwm_widget = tab.sequence_table.cellWidget(1, 2)
        smoke_fan_widget = tab.sequence_table.cellWidget(1, 3)
        smoke_pwm_widget = tab.sequence_table.cellWidget(1, 4)

        self.assertAlmostEqual(float(duration_widget.value()), 1.0)
        self.assertEqual(bool(main_fan_widget.currentData()), False)
        self.assertEqual(int(main_pwm_widget.value()), 0)
        self.assertEqual(bool(smoke_fan_widget.currentData()), False)
        self.assertEqual(int(smoke_pwm_widget.value()), 0)


if __name__ == "__main__":
    unittest.main()
