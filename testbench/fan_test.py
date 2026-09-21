"""
Interaktiv hardware test af PWM og RPM (FG-signal).
Opdateret med udvidet spin-up time for stabil aflæsning.

Kørsel af dette script starter en terminal-prompt, hvor du kan 
indtaste ønsket PWM-procent. Ventilatoren spinder op (4 sek. ventetid), 
tager 10 RPM-målinger (via FG-kablet), udregner gennemsnittet, 
udskriver det i terminalen og slukker derefter sikkert.
"""

from __future__ import annotations

import time
import config
from hardware.fans import FanController
from hardware.fan_rpm import FanRPMMonitor

def main() -> None:
    # Sætter GPIO pin til FG-signalet op (Henter fra config, ellers bruges 17)
    fg_gpio = getattr(config, "MAIN_FAN_FG_GPIO", 17)

    # Initialisér hardware-klasser fra dine filer
    fan = FanController(gpio_pin=config.MAIN_FAN_PWM_GPIO, name="Main Fan")
    rpm_monitor = FanRPMMonitor(gpio_pin=fg_gpio, name="Main Fan RPM")

    print("\n" + "="*50)
    print(" INTERAKTIV FG (RPM) & PWM TESTBÆNK (Udvidet Spin-up)")
    print("="*50)
    print(f"PWM (Gul) GPIO: {fan.gpio_pin} | FG (Blå) GPIO: {rpm_monitor.gpio_pin}")
    print("Skriv 'q' for at afslutte.\n")

    try:
        while True:
            user_input = input("\nIndtast ønsket hastighed 0-100% (eller 'q' for at afslutte): ").strip()
            
            if user_input.lower() == 'q':
                break
            
            try:
                pwm_val = int(user_input)
            except ValueError:
                print("Ugyldigt input. Indtast venligst et tal mellem 0 og 100.")
                continue

            # Forsøg at sætte PWM og tænde ventilatoren
            try:
                fan.set_pwm(pwm_val)
                fan.on()
            except ValueError as e:
                print(f"Fejl: {e}")
                continue

            print(f"\n--> Starter blæser på {pwm_val}%...")
            print("--> Venter 4 sekunder på fuldt spin-up...")
            time.sleep(4.0)

            print("\n--- Tager 10 RPM-målinger ---")
            measurements = []
            
            for i in range(1, 11):
                # Hent RPM måling fra den blå ledning via FanRPMMonitor
                current_rpm = rpm_monitor.get_rpm()
                
                if current_rpm is not None:
                    print(f"  Måling {i:02d}: {current_rpm} RPM")
                    measurements.append(current_rpm)
                else:
                    print(f"  Måling {i:02d}: -- (Ingen rotation / Venter på data)")
                
                time.sleep(0.5)
            
            # Beregn og vis det endelige gennemsnit af de 10 målinger
            if measurements:
                avg_rpm = sum(measurements) / len(measurements)
                print(f"\n==> Gennemsnitlig RPM ved {pwm_val}%: {avg_rpm:.1f} RPM")
            else:
                print("\n==> FEJL: Fik ingen gyldige målinger. Tjek den BLÅ FG-forbindelse.")
            
            print("\nSlukker ventilator og venter på næste input...")
            fan.off()

    except KeyboardInterrupt:
        print("\nTest afbrudt manuelt (Ctrl+C).")
    except Exception as exc:
        print(f"\nUventet fejl: {exc}")
    finally:
        print("\nRydder op i hardware forbindelser...")
        fan.cleanup()
        rpm_monitor.cleanup()
        print("Afsluttet.")

if __name__ == "__main__":
    main()