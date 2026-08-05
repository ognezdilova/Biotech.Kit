"""To start the EMG data acquisition, run the following command in your terminal from the root directory of the project BK/:

```
-m app.main
```

This will list the available COM ports, connect to the specified device, and start recording EMG data. Press Ctrl+C to stop the recording."""


import serial

from app.core.session import AcquisitionSession
from app.devices.serial_device import SerialDevice, list_available_ports
from app.parsers.esp32_emg_parser import ESP32EMGParser
from app.storage.csv_sink import CSVSink

def main() -> None:
    print("Available COM ports:")
    for port in list_available_ports():
        print(f"  {port}")

    device = SerialDevice(port="COM4", baudrate=115200)
    parser = ESP32EMGParser()
    sinks = [CSVSink(output_dir="data/recordings")]

    session = AcquisitionSession(device=device, parser=parser, sinks=sinks)

    print("Press Ctrl+C to stop recording...\n")
    try:
        session.run()
        
    except KeyboardInterrupt:
        print(f"\nRecording stopped. Total samples: {session.sample_count}")
    except (ConnectionError, serial.SerialException) as e:
        print(f"Connection error: {e}")


if __name__ == "__main__":
    main()