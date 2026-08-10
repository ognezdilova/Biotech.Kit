"""To start the EMG data acquisition, run the following command in your terminal from the root directory of the project BK/:

```
python -m app.main                     Uses the first available COM port
python -m app.main --port <COM_PORT>   Specify a COM port (e.g., COM4, COM7)
python -m app.main --help              Shows help
```

This will list the available COM ports, connect to the specified device, and start recording EMG data. Press Ctrl+C to stop the recording."""


import argparse
import sys

import serial

from core.digital_signal_processing.dsp_base import SignalProcessor
from core.digital_signal_processing.filters import BandpassFilter, NotchFilter
from core.session import AcquisitionSession
from app.devices.serial_device import SerialDevice, list_available_ports
from app.parsers.esp32_emg_parser import ESP32EMGParser
from app.storage.csv_sink import CSVSink

# Hardware-specific configuration (ESP32 + BioAmp EXG)
SAMPLE_RATE_HZ = 1000.0  # matches firmware SAMPLE_RATE
POWERLINE_FREQ_HZ = 60.0  # 60 Hz for North America (use 50.0 for most other regions)
EMG_BANDPASS_LOW_HZ = 20.0
EMG_BANDPASS_HIGH_HZ = 400.0
EMG_BANDPASS_ORDER = 4


def main() -> None:
    parser_cli = argparse.ArgumentParser(
        description="Start EMG data acquisition from ESP32 device."
    )
    parser_cli.add_argument(
        "--port",
        type=str,
        default=None,
        help="Serial port to connect to (e.g., COM4, COM7). If not specified, uses the first available port.",
    )
    args = parser_cli.parse_args()

    available_ports = list_available_ports()
    print("Available COM ports:")
    if not available_ports:
        print("  (none found)")
        sys.exit(1)
    for port in available_ports:
        print(f"  {port}")

    # Determine which port to use
    if args.port:
        selected_port = args.port
        if selected_port not in available_ports:
            print(f"\nWarning: Specified port {selected_port} not found in available ports.")
            print("Attempting to connect anyway...")
    else:
        selected_port = available_ports[0]
        print(f"\nNo port specified, using first available: {selected_port}")

    print(f"Connecting to {selected_port}...")

    device = SerialDevice(port=selected_port, baudrate=115200)
    parser = ESP32EMGParser()
    
    # Raw data sink (always preserved unmodified)
    raw_sink = CSVSink(output_dir="data/recordings")
    
    # DSP chain: notch filter (powerline rejection) -> bandpass (EMG band isolation)
    processor = SignalProcessor(
        filters=[
            NotchFilter(notch_hz=POWERLINE_FREQ_HZ, sample_rate_hz=SAMPLE_RATE_HZ),
            BandpassFilter(
                low_hz=EMG_BANDPASS_LOW_HZ,
                high_hz=EMG_BANDPASS_HIGH_HZ,
                sample_rate_hz=SAMPLE_RATE_HZ,
                order=EMG_BANDPASS_ORDER,
            ),
        ]
    )
    
    # Filtered data sink (separate file with "_filtered" suffix)
    filtered_sink = CSVSink(output_dir="data/recordings", filename_suffix="_filtered")
    
    session = AcquisitionSession(
        device=device,
        parser=parser,
        sinks=[raw_sink],
        processor=processor,
        processed_sinks=[filtered_sink],
    )

    print("Press Ctrl+C to stop recording...\n")
    try:
        session.run()
        
    except KeyboardInterrupt:
        print(f"\nRecording stopped. Total samples: {session.sample_count}")
    except (ConnectionError, serial.SerialException) as e:
        print(f"Connection error: {e}")


if __name__ == "__main__":
    main()