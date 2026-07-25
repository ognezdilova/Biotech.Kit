## Version 0.0.1

### Major Changes
- **ESP32 Firmware**: Modified to stream both timestamp (`t_next`) and raw ADC values in CSV format (timestamp,raw_value) over serial at 115200 baud
- **Python Data Recorder**: Created `main.py` to read serial data from COM4, parse CSV format, and save to timestamped CSV files in `data/recordings/`
- **Automatic Port Detection**: Added function to list and validate available COM ports before attempting connection

### Minor Changes
- Added `serial.tools.list_ports` integration for COM port enumeration and validation
- Implemented automatic directory creation for recording output (`data/recordings/`)
- Added timestamped filename generation for EMG data files (`emg_data_YYYYMMDD_HHMMSS.csv`)
- Display progress counter every 1000 samples during recording
- Added CSV header row for better data organization (timestamp, raw_value)

### Fixed
- Serial port freezing issues on Windows by disabling hardware flow control (dsrdtr, rtscts, xonxoff)
- Port access issues with deferred opening pattern (create Serial object before calling `.open()`)
- Added write timeout to prevent blocking on write operations
- Improved error handling for port availability and connection failures


