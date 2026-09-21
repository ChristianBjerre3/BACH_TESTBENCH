"""
Interaktiv hardware test af PWM og RPM for AGCO Airflow Smoke Test Bench.

Kørsel af dette script starter en terminal-prompt, hvor du kan 
indtaste ønsket PWM-procent. Ventilatoren spinder op, tager 
10 RPM-målinger over 5 sekunder, udregner gennemsnittet og slukker.
"""

from __future__ import annotations

import time
import config
from hardware.fans import FanController
from hardware.fan_rpm import FanRPMMonitor

def main() -> None:
    # Hent GPIO pin til FG-signalet (hvis den ikke findes i config, bruges 17 som standard)
    fg_gpio = getattr(config, "MAIN_FAN_FG_GPIO", 17)

    # Initialisér hardware-klasser
    fan = FanController(gpio_pin=config.MAIN_FAN_PWM_GPIO, name="Main Fan")
    rpm_monitor = FanRPMMonitor(gpio_pin=fg_gpio, name="Main Fan RPM")

    print("\n" + "="*50)
    print(" INTERAKTIV VENTILATOR TESTBÆNK")
    print("="*50)
    print(f"PWM GPIO: {fan.gpio_pin} | FG (RPM) GPIO: {rpm_monitor.gpio_pin}")
    print("Skriv 'q' for at afslutte.\n")

    try:
        while True:
            user_input = input("Indtast ønsket PWM procent (eller 'q' for at afslutte): ").strip()
            
            if user_input.lower() == 'q':
                break
            
            try:
                pwm_val = int(user_input)
            except ValueError:
                print("Ugyldigt input. Indtast venligst et heltal.")
                continue

            # Forsøg at sætte PWM og tænde. FanController kaster en ValueError, 
            # hvis værdien ikke findes i config.PWM_LEVELS
            try:
                fan.set_pwm(pwm_val)
                fan.on()
            except ValueError as e:
                print(f"\nFejl: {e}\n")
                continue

            print(f"\n-> Ventilatoren sættes til {pwm_val}%...")
            print("-> Venter 2 sekunder på spin-up...")
            time.sleep(2.0)

            print("-> Tager 10 RPM-målinger (1 pr. halve sekund):")
            measurements = []
            
            for i in range(1, 11):
                current_rpm = rpm_monitor.get_rpm()
                
                if current_rpm is not None:
                    print(f"   Måling {i:02d}/10: {current_rpm} RPM")
                    measurements.append(current_rpm)
                else:
                    print(f"   Måling {i:02d}/10: -- (Venter på data / Ingen rotation)")
                
                time.sleep(0.5)
            
            # Beregn gennemsnit hvis vi fik gyldige målinger
            if measurements:
                avg_rpm = sum(measurements) / len(measurements)
                print(f"\n==> Gennemsnitlig RPM ved {pwm_val}%: {avg_rpm:.1f} RPM")
            else:
                print("\n==> Fik ingen gyldige RPM-målinger. Tjek FG-forbindelsen eller pull-up modstanden.")
            
            print("\nSlukker ventilator...\n")
            fan.off()

    except KeyboardInterrupt:
        print("\nTest afbrudt af bruger (Ctrl+C).")
    except Exception as exc:
        print(f"\nDer opstod en uventet fejl: {exc}")
    finally:
        print("Rydder sikkert op i GPIO...")
        fan.cleanup()
        rpm_monitor.cleanup()
        print("Oprydning færdig.")

if __name__ == "__main__":
    main()