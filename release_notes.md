## Version 0.2.0 - DSP Integration and Replay Capability

### Major Changes
- **Real-time DSP Processing**: Integrated signal processing into live acquisition pipeline
  - `core/digital_signal_processing/dsp_base.py`: Filter ABC and SignalProcessor for composable filter chains
  - `core/digital_signal_processing/filters.py`: NotchFilter (IIR, 60Hz powerline rejection) and BandpassFilter (Butterworth, EMG band isolation)
  - Sample-by-sample causal processing with warm-start via lfilter_zi (no startup transient)
  - Dual-output architecture: raw samples always preserved, filtered samples to separate sinks
- **ReplayDevice**: Replay CSV recordings through AcquisitionDevice interface
  - `core/replay_device.py`: Transparent offline data source for validation and testing
  - Configurable playback speed (1.0 = real-time, 2.0 = 2x, 0 = max speed)
  - Fallback synthetic timing via sample_rate parameter when timestamps unavailable
  - Same interface as live devices - works seamlessly with AcquisitionSession
- **Enhanced AcquisitionSession**: Support for optional SignalProcessor and processed_sinks
  - Raw samples always go to `sinks` unmodified (preserves original recordings)
  - Filtered samples go to `processed_sinks` (separate CSV files with "_filtered" suffix)
  - Both pipelines run simultaneously during acquisition
- **Validation Tools**:
  - `scripts/validate_dsp.py`: Offline DSP validation with matplotlib side-by-side plots
  - `scripts/view_csv.py`: CSV data viewer with multi-channel support and time-axis reconstruction
- **CLI Enhancements**: Flexible port selection in app/main.py
  - Added argparse `--port` flag for explicit port selection
  - Auto-selects first available port if not specified
  - Clear feedback about port selection and connection status

### Architecture Changes
- **Sample.value Type Widening**: Changed from `int` to `int | float`
  - Raw ADC readings remain int (from parser)
  - Filtered signal values are float (from SignalProcessor)
  - Added tech debt note for future RawSample/ProcessedSample split
- **CSVSink Enhancement**: Added `filename_suffix` parameter
  - Supports separate output files for raw and filtered data
  - Format: `emg_data_TIMESTAMP.csv` (raw), `emg_data_TIMESTAMP_filtered.csv` (filtered)
  - Backward compatible (suffix defaults to empty string)

### Technology Stack Updates
- Added **SciPy 1.18** for IIR filter design (butter, iirnotch, lfilter)
- Added **NumPy 2.5** for numerical operations
- Added **Matplotlib 3.11** for signal visualization
- Added **Pandas 3.0** for CSV data manipulation

### Hardware-Specific Configuration
- Added config constants in main.py for ESP32 + BioAmp EXG:
  - SAMPLE_RATE_HZ = 1000.0
  - POWERLINE_FREQ_HZ = 60.0 (configurable for 50Hz regions)
  - EMG_BANDPASS_LOW_HZ = 20.0
  - EMG_BANDPASS_HIGH_HZ = 400.0
  - EMG_BANDPASS_ORDER = 4

### Fixed
- Bug in AcquisitionSession.run(): processed_sinks were closed but never opened
- ReplayDevice now uses file.seek(0) instead of close/reopen for efficiency
- Iterator[list[str]] type hint instead of csv.reader for correctness

### Testing
- Validated DSP filters offline using ReplayDevice + validate_dsp.py
- Confirmed dual-output (raw + filtered) in live acquisition
- Tested CLI port selection with auto-detection

---

## Version 0.1.0 - Modular Architecture Refactor

### Major Changes
- **Modular Architecture**: Complete refactor using dependency inversion with abstract base classes
  - `AcquisitionDevice` interface for all data sources (serial, BLE, file replay, etc.)
  - `SignalParser` interface for protocol-specific parsing
  - `DataSink` interface for output destinations (CSV, plots, databases, etc.)
  - `AcquisitionSession` orchestrator that ties device → parser → sinks together
- **Core Abstractions**: Created top-level `core/` package with abstract interfaces:
  - `device.py`: Device abstraction with `open()`, `close()`, `read_line()`
  - `parser.py`: Parser abstraction with `parse()` method
  - `sink.py`: Sink abstraction with `open()`, `write()`, `close()`
  - `session.py`: Session orchestration with error handling
  - `models.py`: Shared `Sample` dataclass with multi-channel support
- **Concrete Implementations**: Separated interface from implementation
  - `devices/serial_device.py`: Serial/UART device with port enumeration
  - `parsers/esp32_emg_parser.py`: CSV format parser for ESP32 firmware
  - `storage/csv_sink.py`: CSV file writer with automatic flushing
- **Tested on Real Hardware**: All components validated with live ESP32 EMG acquisition

### Architecture Benefits
- Easy to swap devices (serial → BLE → file replay) without touching parser or sink code
- Multiple sinks can run simultaneously (CSV + real-time plot + database)
- New protocols can be added by implementing `SignalParser` without modifying session logic
- Clean separation of concerns following SOLID principles

### Minor Changes
- Added type hints throughout (Python 3.10+ union syntax)
- Context manager support for devices and sinks
- Progress reporting every 1000 samples
- Automatic CSV file timestamping (`emg_data_YYYYMMDD_HHMMSS.csv`)
- Port validation before connection attempt
- Graceful handling of malformed data lines

### Fixed
- Parameter name typo: `sink` → `sinks` in `AcquisitionSession.__init__()`
- Serial port freezing on Windows (disabled hardware flow control)
- Write timeout to prevent blocking operations
- Proper cleanup in exception handling (sinks always closed)

---

## Version 0.0.1 - Initial Prototype

### Major Changes
- ESP32 firmware streaming timestamp and raw ADC values in CSV format
- Basic Python data recorder with serial communication
- Automatic port detection and validation

### Fixed
- Initial serial communication issues on Windows


