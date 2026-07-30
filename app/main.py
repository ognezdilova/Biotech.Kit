import serial
import serial.tools.list_ports
import csv
from datetime import datetime
import os

# List available COM ports
def list_available_ports():
    """List all available COM ports."""
    ports = serial.tools.list_ports.comports()
    available = []
    print("\nAvailable COM ports:")
    for port in ports:
        print(f"  {port.device} - {port.description}")
        available.append(port.device)
    return available

"""
    Read EMG data from serial port and save to CSV file.
    Data format: timestamp,raw_value
    """

def read_emg_data(port='COM4', baudrate=115200, output_dir='data/recordings'):
    
    # Check if port exists
    available_ports = list_available_ports()
    if not available_ports:
        print("\nNo COM ports found! Make sure your device is connected.")
        return
    
    if port not in available_ports:
        print(f"\n{port} not found! Available ports: {', '.join(available_ports)}")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = os.path.join(output_dir, f'emg_data_{timestamp}.csv')
    
    print(f"\nConnecting to {port} at {baudrate} baud...")
    
    for p in serial.tools.list_ports.comports():
        print(f"Port: {p.device}, Description: {p.description}, HWID: {p.hwid}") 

    try:
        # Create Serial object without opening (Windows-specific workaround)
        ser = serial.Serial()
        ser.port = port
        ser.baudrate = baudrate
        ser.timeout = 1
        ser.write_timeout = 0
        # ser.dsr= False
        # ser.rts = False
        ser.dsrdtr = False
        ser.rtscts = False
        ser.xonxoff = False
        
        # Now open the port
        print("Opening port...")
        ser.open()
        print(f"Connected! Saving data to {csv_filename}")
        print("Press Ctrl+C to stop recording...\n")
        
        # Open CSV file for writing
        with open(csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'raw_value'])  # Header
            
            sample_count = 0
            
            while True:
                try:
                    # Read line from serial
                    line = ser.readline().decode('utf-8').strip()
                    
                    if line:
                        # Parse comma-separated values
                        parts = line.split(',')
                        if len(parts) == 2:
                            timestamp_us, raw_value = parts
                            writer.writerow([timestamp_us, raw_value])
                            
                            sample_count += 1
                            if sample_count % 1000 == 0:
                                print(f"Recorded {sample_count} samples...")
                                csvfile.flush()  # Ensure data is written to disk
                        
                except UnicodeDecodeError:
                    continue
                    
    except KeyboardInterrupt:
        print(f"\n\nRecording stopped. Total samples: {sample_count}")
        print(f"Data saved to: {csv_filename}")
        
    except serial.SerialException as e:
        print(f"Serial port error: {e}")
        print(f"Make sure the device is connected to {port}")
        
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == "__main__":
    read_emg_data()