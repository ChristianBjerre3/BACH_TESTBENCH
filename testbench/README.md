# Airflow / smoke test bench (Raspberry Pi 4)

Python/PySide6 application skeleton for controlling and logging a small airflow/smoke test bench on a **Raspberry Pi 4**.

This repository currently contains **project structure and placeholders only**. Hardware control, logging, plotting and GUI behaviour will be implemented incrementally, file by file.

## Purpose

The Raspberry Pi controls two 12 V BLDC fans (via MOSFETs), two OPT101 optical sensors (via ADS1115), and two associated LEDs. A smoke machine is operated **manually**; the GUI only logs whether the operator considers it ON or OFF.

## Target platform

- Raspberry Pi 4
- Python 3
- BCM GPIO numbering

## Fixed pinout

| Function              | Connection                          |
|-----------------------|-------------------------------------|
| Main fan PWM          | GPIO18                              |
| Smoke fan PWM         | GPIO13                              |
| LED 1 (sensor 1)      | GPIO23                              |
| LED 2 (sensor 2)      | GPIO24                              |
| I2C SDA               | GPIO2                               |
| I2C SCL               | GPIO3                               |
| OPT101 sensor 1       | ADS1115 A0                          |
| OPT101 sensor 2       | ADS1115 A1                          |

## Planned GUI tabs

1. **CONTROL** – fans, smoke-machine log toggle, sensors, recording, STOP ALL  
2. **LIVE DATA** – live voltages, states, elapsed time, plots (~10 Hz)  
3. **SEQUENCE** – automated fan sequences (smoke machine not electrically controlled)

## Layout

```
testbench/
├── main.py
├── config.py
├── hardware/     # fans, sensors, LEDs, ADC placeholders
├── services/     # logger, sequence engine, test session
├── gui/          # main window + three tabs
├── data/         # future CSV experiment files
└── sequences/    # future sequence definitions
```

## Development note

Do not expect `main.py` or the GUI modules to run a full application yet. Constants live in `config.py`; each module documents TODOs for the next implementation step.

## Dependencies

See `requirements.txt` (PySide6, pyqtgraph, GPIO stack, Adafruit ADS1x15). Install on the Pi when starting real implementation.
