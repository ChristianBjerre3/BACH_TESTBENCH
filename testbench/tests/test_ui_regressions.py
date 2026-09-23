import unittest

from PySide6.QtWidgets import QApplication

from gui.control_tab import ControlTab
from gui.live_tab import LiveTab
from gui.sequence_tab import SequenceTab


class UiRegressionTests(unittest.TestCase):
    def test_control_pwm_controls_are_numeric_and_range_5_to_100(self):
        app = QApplication.instance() or QApplication([])
        tab = ControlTab()

        self.assertEqual(tab.main_fan_pwm_combo.minimum(), 5)
        self.assertEqual(tab.main_fan_pwm_combo.maximum(), 100)
        self.assertEqual(tab.smoke_fan_pwm_combo.minimum(), 5)
        self.assertEqual(tab.smoke_fan_pwm_combo.maximum(), 100)

    def test_live_sensor_plot_has_fixed_voltage_axis_0_to_2_6(self):
        app = QApplication.instance() or QApplication([])
        tab = LiveTab()

        y_min, y_max = tab.plot.getAxis("left").range
        self.assertAlmostEqual(y_min, 0.0)
        self.assertAlmostEqual(y_max, 2.6)

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
