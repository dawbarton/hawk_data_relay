import logging
import struct
import threading
import time
from io import TextIOWrapper
from pathlib import Path

import serial
from cobs import cobs

from .buffer import RingBuffer
from .config import Config

logger = logging.getLogger(__name__)


class SerialReader(threading.Thread):
    def __init__(self, config: Config, buffer: RingBuffer, log_file: TextIOWrapper, cmd_log_file: TextIOWrapper):
        super().__init__(daemon=True)
        self._config = config
        self._buffer = buffer
        self._log_file = log_file
        self._cmd_log_file = cmd_log_file
        self._stop_event = threading.Event()
        # Shared serial port and lock — also used by the API to send commands
        self.ser: serial.Serial | None = None
        self.serial_lock = threading.Lock()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        expected_len = self._config.num_floats * 4
        fmt = f"<{self._config.num_floats}f"

        while not self._stop_event.is_set():
            try:
                with self.serial_lock:
                    self.ser = serial.Serial(
                        self._config.port,
                        self._config.baud,
                        timeout=1,
                    )
                logger.info("Opened serial port %s at %d baud", self._config.port, self._config.baud)
                self._read_loop(expected_len, fmt)
            except serial.SerialException as exc:
                logger.warning("Serial error: %s — retrying in 2 s", exc)
                with self.serial_lock:
                    if self.ser and self.ser.is_open:
                        self.ser.close()
                    self.ser = None
                self._stop_event.wait(timeout=2)

        with self.serial_lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self.ser = None

    def _read_loop(self, expected_len: int, fmt: str) -> None:
        buf = bytearray()
        while not self._stop_event.is_set():
            try:
                byte = self.ser.read(1)
            except serial.SerialException as exc:
                logger.warning("Read error: %s", exc)
                raise

            if not byte:
                continue

            if byte == b"\x00":
                if buf:
                    try:
                        decoded = cobs.decode(bytes(buf))
                        if len(decoded) == expected_len:
                            values = list(struct.unpack(fmt, decoded))
                            ts = time.time()
                            self._buffer.push(ts, values)
                            self._log_file.write(
                                f"{ts:.6f}," + ",".join(f"{v:.6f}" for v in values) + "\n"
                            )
                            self._log_file.flush()
                        else:
                            logger.debug(
                                "Frame length mismatch: got %d bytes, expected %d",
                                len(decoded),
                                expected_len,
                            )
                    except cobs.DecodeError as exc:
                        logger.debug("COBS decode error: %s", exc)
                    buf.clear()
            else:
                buf.extend(byte)

    def send_command(self, values: list[float]) -> None:
        packed = struct.pack(f"<{len(values)}f", *values)
        encoded = cobs.encode(packed) + b"\x00"
        with self.serial_lock:
            if self.ser is None or not self.ser.is_open:
                raise RuntimeError("Serial port is not open")
            self.ser.write(encoded)
        ts = time.time()
        self._cmd_log_file.write(
            f"{ts:.6f}," + ",".join(f"{v:.6f}" for v in values) + "\n"
        )
        self._cmd_log_file.flush()
