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


