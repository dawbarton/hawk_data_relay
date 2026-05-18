import argparse
import logging
from datetime import datetime
from pathlib import Path

import uvicorn

from .api import app, init
from .buffer import RingBuffer
from .config import Config
from .serial_reader import SerialReader


def parse_args() -> tuple[Config, str]:
    parser = argparse.ArgumentParser(
        description="hawk-data-relay: serial-to-HTTP bridge for MCU experiment data"
    )
    parser.add_argument("--port", required=True, help="Serial port (e.g. COM3 or /dev/tty.usbserial-0001)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--num-floats", type=int, default=10, help="Number of float32 values per frame (default: 10)")
    parser.add_argument("--host", default="127.0.0.1", help="API listen address (default: 127.0.0.1)")
    parser.add_argument("--api-port", type=int, default=5000, help="API listen port (default: 5000)")
    parser.add_argument("--log-dir", type=Path, default=Path("logs"), help="Directory for log files (default: ./logs)")
    parser.add_argument("--buffer-maxlen", type=int, default=50000, help="Max frames in memory (default: 50000)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    return Config(
        port=args.port,
        baud=args.baud,
        num_floats=args.num_floats,
        host=args.host,
        api_port=args.api_port,
        log_dir=args.log_dir,
        buffer_maxlen=args.buffer_maxlen,
    ), args.log_level


def main() -> None:
    config, log_level = parse_args()

    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    config.log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = config.log_dir / f"experiment_{timestamp}.csv"
    cmd_log_path = config.log_dir / f"commands_{timestamp}.csv"

    # Write CSV headers
    channel_names = ",".join(f"ch{i}" for i in range(config.num_floats))
    log_file = log_path.open("a", buffering=1)  # line-buffered
    log_file.write(f"# timestamp,{channel_names}\n")

    cmd_log_file = cmd_log_path.open("a", buffering=1)  # line-buffered
    cmd_log_file.write("# timestamp,val0,val1,...\n")

    buffer = RingBuffer(maxlen=config.buffer_maxlen)
    reader = SerialReader(config, buffer, log_file, cmd_log_file)

    init(config, buffer, reader, str(log_path), str(cmd_log_path))

    reader.start()
    logger.info("Serial reader started")
    logger.info("Log file: %s", log_path)
    logger.info("Command log file: %s", cmd_log_path)
    logger.info("API at http://%s:%d — docs at http://%s:%d/docs", config.host, config.api_port, config.host, config.api_port)

    try:
        uvicorn.run(app, host=config.host, port=config.api_port, log_level=log_level.lower())
    finally:
        logger.info("Shutting down...")
        reader.stop()
        reader.join(timeout=5)
        log_file.close()
        cmd_log_file.close()
        logger.info("Done")


if __name__ == "__main__":
    main()
