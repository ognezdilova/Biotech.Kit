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
* **Real-time DSP Processing**: Complete EMG envelope extraction pipeline
  - Notch filter (powerline rejection)
  - Bandpass filter (EMG band isolation)
  - Full-wave rectification (envelope preparation)
  - Low-pass filter (continuous envelope smoothing)
* **Block-based Signal Processing**: WindowBuffer for windowed analysis (RMS, FFT-ready)
* **Windowing & Buffering**: Efficient circular buffering with configurable window sizes and overlap
* **RMS Processor**: Root-mean-square amplitude computation for muscle activation measurement
* **Envelope Detection**: Continuous, low-latency envelope extraction via rectification + low-pass filtering
* **Recording Replay**: ReplayDevice for offline analysis and DSP validation
* **CSV Recording**: Timestamped data files with automatic directory management
* **Multiple Data Sinks**: Support for simultaneous data outputs (CSV, future: real-time plots, databases)
* **CLI Port Selection**: Flexible port selection with auto-detection fallback
* **Robust Serial Communication**: Hardware flow control disabled for Windows compatibility
* **Progress Monitoring**: Real-time sample counting during acquisition
* **Error Handling**: Graceful handling of malformed data and connection issues
* **Validation Tools**: Offline DSP validation, envelope comparison, buffering validation, and CSV visualization scripts

---

## Planned Features

* Real-time visualization (matplotlib integration)
* Advanced signal processing modules (spectral analysis, FFT, frequency-domain features)
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

* **ESP32 Nano microcontroller** (tested on real hardware)
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
│       ├── dsp_base.py            # Filter ABC, SignalProcessor, BlockProcessor ABC
│       ├── filters.py             # NotchFilter, BandpassFilter, RectificationFilter, LowpassFilter
│       ├── buffering.py           # RingBuffer, Window, WindowBuffer
│       └── block_processors.py    # RMSProcessor (concrete BlockProcessors)
│
├── scripts/
│   ├── validate_dsp.py            # Offline DSP validation tool
│   ├── validate_buffering.py      # Windowing/buffering validation tool
│   ├── validate_rms.py            # RMS visualization tool
│   └── view_csv.py                # CSV visualization utility
│
├── data/
│   └── recordings/                # Timestamped CSV output files
├── firmware/
│   └── sketch_jul15a/             # ESP32 Arduino firmware
│
├── release_notes.md
│
├── requirements.txt
│
└── README.md
```

---

## Signal Processing Pipeline

BK implements a complete real-time EMG envelope extraction pipeline using causal IIR filters:

### Sample-by-Sample Processing Chain

```
Raw EMG (1000 Hz)
    ↓
NotchFilter (60 Hz)          # Powerline interference rejection
    ↓
BandpassFilter (20-400 Hz)   # EMG frequency band isolation
    ↓
RectificationFilter          # Full-wave rectification: abs(x)
    ↓
LowpassFilter (8 Hz)         # Envelope smoothing
    ↓
Continuous Envelope          # Smooth muscle activation level
```

### Filter Characteristics

| Filter | Type | Purpose | Latency |
|--------|------|---------|---------|
| **NotchFilter** | IIR (iirnotch) | Remove 60 Hz powerline interference | ~10 ms |
| **BandpassFilter** | Butterworth 4th-order | Isolate EMG band (20-400 Hz) | ~20 ms |
| **RectificationFilter** | Stateless | Convert bipolar signal to unipolar | 0 ms |
| **LowpassFilter** | Butterworth 4th-order | Smooth envelope (8 Hz cutoff) | ~50 ms |
| **Total Pipeline** | | | **~80-100 ms** |

All filters are:
- **Causal**: Output depends only on current and past samples (real-time capable)
- **Stateful**: Maintain internal state (`zi` coefficients) across samples
- **Warm-started**: Initialized with first sample to avoid startup transients

### Block-Based Processing (Optional)

For windowed analysis, samples can also be fed to `WindowBuffer` → `RMSProcessor`:

```
Rectified Signal → WindowBuffer (256 samples, 128 hop) → RMSProcessor → Discrete RMS values
```

This provides an alternative envelope extraction approach (RMS) useful for research comparisons and offline analysis.

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
- `data/recordings/emg_data_YYYYMMDD_HHMMSS_filtered.csv` (processed envelope: notch + bandpass + rectification + lowpass 8Hz)

The filtered output contains a continuous, smooth envelope of muscle activation suitable for real-time visualization and control applications.

### Offline DSP Validation

Validate the complete DSP pipeline and visualize the continuous envelope:
```bash
python -m scripts.validate_dsp data/recordings/emg_data_YYYYMMDD_HHMMSS.csv
```

This displays side-by-side plots of raw EMG signal vs. the processed envelope (notch + bandpass + rectification + lowpass).

### RMS Envelope Comparison

Compare continuous low-pass envelope vs. windowed RMS envelope:
```bash
python -m scripts.validate_rms data/recordings/emg_data_YYYYMMDD_HHMMSS.csv
python -m scripts.validate_rms data/recordings/emg_data_YYYYMMDD_HHMMSS.csv --window-size 128 --lowpass-cutoff 10
```

This demonstrates two envelope extraction approaches:
- **Low-pass envelope**: Continuous, sample-by-sample, low latency (~50-100ms)
- **RMS envelope**: Windowed, block-based, standard for research

Both use the same preprocessing (notch → bandpass → rectification), then either low-pass filtering or RMS computation.

### Windowing & Buffering Validation

Validate the windowing system with recorded data:
```bash
python -m scripts.validate_buffering data/recordings/emg_data_YYYYMMDD_HHMMSS.csv
python -m scripts.validate_buffering data/recordings/emg_data_YYYYMMDD_HHMMSS.csv --window-size 256 --hop-size 128
python -m scripts.validate_buffering data/recordings/emg_data_YYYYMMDD_HHMMSS.csv --channel 0
```

This replays recorded data through the WindowBuffer pipeline and displays per-window statistics (sample rate, min/max/mean values, RMS). The buffering layer uses a circular buffer to create fixed-size, optionally overlapping windows from the continuous signal stream - essential for block-based analysis like FFT and RMS computation.

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

