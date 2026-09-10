"""To start the EMG data acquisition, run the following command in your terminal from the root directory of the project BK/:

```
python -m app.main                     Uses the first available COM port
python -m app.main --port <COM_PORT>   Specify a COM port (e.g., COM4, COM7)
python -m app.main --help              Shows help
```

This will list the available COM ports, connect to the specified device, and start recording EMG data. Press Ctrl+C to stop the recording."""


import argparse
import signal
import sys
import threading
import serial

from core.digital_signal_processing.dsp_base import SignalProcessor
from core.digital_signal_processing.filters import (
    BandpassFilter,
    LowpassFilter,
    NotchFilter,
    RectificationFilter,
)
from core.recording import RecordingController, RecordingSampleConsumer
from core.session import AcquisitionSession
from app.devices.serial_device import SerialDevice, list_available_ports
from app.parsers.esp32_emg_parser import ESP32EMGParser
from app.storage.csv_sink import CSVSink

#visualization imports
from app.visualization.stream_plotter import DualChannelRawPlotter
from core.live_buffer import RollingBufferConsumer

# Hardware-specific configuration (ESP32 + BioAmp EXG)
SAMPLE_RATE_HZ = 1000.0  # matches firmware SAMPLE_RATE
POWERLINE_FREQ_HZ = 60.0  # 60 Hz for North America (use 50.0 for most other regions)
EMG_BANDPASS_LOW_HZ = 20.0
EMG_BANDPASS_HIGH_HZ = 400.0
EMG_BANDPASS_ORDER = 4
ENVELOPE_LOWPASS_HZ = 8.0  # Envelope smoothing cutoff (6-10 Hz typical for EMG)


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
    
    # DSP chain: notch -> bandpass -> rectification -> lowpass envelope

    processor = SignalProcessor(
        filters=[
            NotchFilter(notch_hz=POWERLINE_FREQ_HZ, sample_rate_hz=SAMPLE_RATE_HZ),
            BandpassFilter(
                low_hz=EMG_BANDPASS_LOW_HZ,
                high_hz=EMG_BANDPASS_HIGH_HZ,
                sample_rate_hz=SAMPLE_RATE_HZ,
                order=EMG_BANDPASS_ORDER,
            ),
            RectificationFilter(),
            LowpassFilter(cutoff_hz=ENVELOPE_LOWPASS_HZ, sample_rate_hz=SAMPLE_RATE_HZ),
        ]
    )
    
    # Filtered data sink (separate file with "_filtered" suffix)
    filtered_sink = CSVSink(output_dir="data/recordings", filename_suffix="_filtered")
    
    # Recording controllers with explicit lifecycle
    raw_recording = RecordingController(sinks=[raw_sink])
    filtered_recording = RecordingController(sinks=[filtered_sink])
    
    # Wrap recording controllers as sample consumers
    raw_consumer = RecordingSampleConsumer(raw_recording)
    filtered_consumer = RecordingSampleConsumer(filtered_recording)
    
    # Live monitoring buffers (rolling, for plotting - independent of recording)
    raw_plot_buffer = RollingBufferConsumer(capacity=2000)

    session = AcquisitionSession(
        device=device,
        parser=parser,
        consumers=[raw_consumer, raw_plot_buffer],           
        processor=processor,
        processed_consumers=[filtered_consumer],
    )

    # Start recording explicitly before running acquisition
    raw_recording.start_recording()
    filtered_recording.start_recording()
    
    print("Press Ctrl+C to stop recording...\n")

    acquisition_error: list[BaseException] = []
    def _run_session():
        try:
            session.run()
        except BaseException as e:
            acquisition_error.append(e)


    acquisition_thread = threading.Thread(target=_run_session, daemon=True)
    acquisition_thread.start()

    # Set up signal handler for graceful shutdown on Ctrl+C
    shutdown_requested = threading.Event()
    
    def signal_handler(signum, frame):
        print("\nShutdown requested (Ctrl+C)...")
        shutdown_requested.set()
        session.stop()
    
    signal.signal(signal.SIGINT, signal_handler)

    plotter = DualChannelRawPlotter(
        raw_buffer=raw_plot_buffer,
        channels=(0, 1),
        watch_thread=acquisition_thread,
        raw_ylim=(0, 4095),  # 12-bit ADC range
    )
    
    try:
        plotter.start()  # blocks until window closed (by user OR by watch_thread check)
    except KeyboardInterrupt:
        print("\nInterrupted...")
    finally:
        if not shutdown_requested.is_set():
            session.stop()
        
        acquisition_thread.join(timeout=2.0)

        print("\nStopping recording...")
        raw_recording.stop_recording()
        filtered_recording.stop_recording()
        print(f"Total samples: {session.sample_count}")

        if acquisition_error:
            err = acquisition_error[0]
            print(f"Acquisition stopped due to error: {err}")
            if not isinstance(err, (ConnectionError, serial.SerialException)):
                raise err


if __name__ == "__main__":
    main()