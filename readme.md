## Biotech Kit (BK)

## Overview

Biotech Kit (BK) is an ongoing research and engineering project focused on building a modular platform for acquiring, processing, visualizing, and analyzing biosignals.

The current version of the project focuses on creating a software framework capable of receiving signals from biomedical sensors, performing signal processing, recording data, and providing tools for further analysis and machine learning integration.

The long-term goal of biotech Kit is to provide a flexible development environment for prototyping biomedical applications.

---

## Project Status

 **Status: Active Development**

This project is currently under continuous development. Features, architecture, and implementation details may change as new components are designed and tested.

---

## Current Features

* **Modular Architecture**: Abstract interfaces for devices, parsers, and data sinks
* **Real-time EMG Acquisition**: Live streaming from ESP32-based hardware over serial (UART)
* **Real-time DSP Processing**: IIR notch and bandpass filters with dual-output (raw + filtered)
* **Recording Replay**: ReplayDevice for offline analysis and DSP validation
* **CSV Recording**: Timestamped data files with automatic directory management
* **Multiple Data Sinks**: Support for simultaneous data outputs (CSV, future: real-time plots, databases)
* **CLI Port Selection**: Flexible port selection with auto-detection fallback
* **Robust Serial Communication**: Hardware flow control disabled for Windows compatibility
* **Progress Monitoring**: Real-time sample counting during acquisition
* **Error Handling**: Graceful handling of malformed data and connection issues
* **Validation Tools**: Offline DSP validation and CSV visualization scripts

---

## Planned Features

* Real-time visualization (matplotlib integration)
* Advanced signal processing modules (envelope detection, RMS, spectral analysis)
* Multi-channel biosignal acquisition
* Machine learning integration for signal classification
* Additional device implementations (BLE, USB)
* User interface for experiment monitoring and analysis
* Database sink for persistent storage

---

## Technology Stack

### Software

* **Python 3.10+** (uses modern type hints)
* **PySerial 3.5** for serial communication
* **SciPy 1.18** for IIR filter design (signal processing)
* **NumPy 2.5** for numerical operations
* **Matplotlib 3.11** for signal visualization
* **Pandas 3.0** for CSV data manipulation
* Git / GitHub for version control

### Hardware

* **ESP32 microcontroller** (tested on real hardware)
* EMG signal acquisition front-end
* Surface electrodes

---

## Project Structure

The project follows a **dependency inversion** architecture with abstract interfaces:

```
BiotechKit/
│
├── app/
│   ├── main.py                    # Entry point for EMG acquisition
│   ├── devices/                   # Concrete device implementations
│   │   └── serial_device.py       # Serial/UART device
│   ├── parsers/                   # Concrete parser implementations
│   │   └── esp32_emg_parser.py    # ESP32 CSV format parser
│   └── storage/                   # Concrete sink implementations
│       └── csv_sink.py            # CSV file writer
│
├── core/                          # Abstract interfaces (ABC)
│   ├── device.py                  # AcquisitionDevice interface
│   ├── parser.py                  # SignalParser interface
│   ├── sink.py                    # DataSink interface
│   ├── session.py                 # Orchestrates device → parser → sinks
│   ├── models.py                  # Sample dataclass
│   ├── replay_device.py           # CSV replay device implementation
│   └── digital_signal_processing/ # DSP layer
│       ├── dsp_base.py            # Filter ABC, SignalProcessor
│       └── filters.py             # NotchFilter, BandpassFilter
│
├── scripts/
│   ├── validate_dsp.py            # Offline DSP validation tool
│   └── view_csv.py                # CSV visualization utility
│
├── data/
│   └── recordings/                # Timestamped CSV output files
├── firmware/
│   └── sketch_jul15a/             # ESP32 Arduino firmware
├── tests/
└── README.md
```

---

## How to Run

### Live Acquisition with Real-time DSP

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Connect your ESP32** to a USB port and verify it appears (e.g., COM4 on Windows)

3. **Run the acquisition:**
   ```bash
   python -m app.main                     # Auto-select first available port
   python -m app.main --port COM4         # Specify port explicitly
   python -m app.main --help              # Show all options
   ```

4. **Stop recording** with `Ctrl+C`

Data will be saved to:
- `data/recordings/emg_data_YYYYMMDD_HHMMSS.csv` (raw ADC values)
- `data/recordings/emg_data_YYYYMMDD_HHMMSS_filtered.csv` (notch + bandpass filtered)

### Offline DSP Validation

Validate DSP filters against recorded data:
```bash
python -m scripts.validate_dsp data/recordings/emg_data_YYYYMMDD_HHMMSS.csv
```

This displays side-by-side plots of raw vs. filtered signals.

### CSV Visualization

View recorded data:
```bash
python -m scripts.view_csv data/recordings/emg_data_YYYYMMDD_HHMMSS.csv
```

---

## Development Approach

BK is developed using an iterative engineering workflow:

* Feature-based Git branches
* Incremental commits
* Modular software design
* Documentation-driven development
* Hardware and software testing cycles

---

## Author

**Olha Gnezdilova**

Biomedical Engineering student focused on neural engineering, biomedical systems, and neurotechnology development.

---

## Copyright and Usage

Copyright © 2026 Olha Gnezdilova.

All rights reserved.

This repository is publicly available for educational, research, and portfolio review purposes.

Viewing, studying, and evaluating this project is permitted.

No permission is granted to copy, modify, redistribute, publish, sublicense, or use any part of this source code in other projects without explicit written permission from the copyright holder.

For collaboration or licensing inquiries, please contact the author.

---

## Disclaimer

This project is a research and development prototype.

It is not intended for medical diagnosis, treatment, monitoring, or clinical use.

