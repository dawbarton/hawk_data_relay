from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    port: str                        # e.g. "COM3" or "/dev/tty.usbserial-0001"
    baud: int = 460800
    num_floats: int = 10             # number of float32 values per MCU frame
    host: str = "127.0.0.1"
    api_port: int = 5000
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    buffer_maxlen: int = 50000       # maximum frames kept in memory
