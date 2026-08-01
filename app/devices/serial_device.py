"""Concrete AcquisitionDevice implementation over a serial (UART) port."""

import serial
import serial.tools.list_ports

from app.core.device import AcquisitionDevice


def list_available_ports() -> list[str]:
    """Return a list of available COM port device names in the system."""
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]


class SerialDevice(AcquisitionDevice):
    """Acquisition device backed by a serial port (e.g. an ESP32 board)."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0) -> None:
        self._port_name = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._serial: serial.Serial | None = None

    def open(self) -> None:
        available = list_available_ports()
        if self._port_name not in available:
            raise ConnectionError(
                f"Port {self._port_name} not found. "
                f"Available: {', '.join(available) or 'none'}"
            )

        ser = serial.Serial()
        ser.port = self._port_name
        ser.baudrate = self._baudrate
        ser.timeout = self._timeout
        ser.write_timeout = 0
        ser.dsrdtr = False
        ser.rtscts = False
        ser.xonxoff = False
        ser.open()

        self._serial = ser

    def read_line(self) -> str | None:
        if self._serial is None:
            raise RuntimeError("Device is not open. Call open() first.")

        try:
            line = self._serial.readline().decode("utf-8").strip()
            return line or None
        except UnicodeDecodeError:
            return None

    def close(self) -> None:
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
        self._serial = None