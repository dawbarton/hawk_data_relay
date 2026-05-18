from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from .buffer import RingBuffer
from .config import Config
from .serial_reader import SerialReader

app = FastAPI(title="hawk-data-relay")

# Populated by main.py before the server starts
_buffer: RingBuffer | None = None
_reader: SerialReader | None = None
_config: Config | None = None
_log_path: str = ""
_cmd_log_path: str = ""


def init(config: Config, buffer: RingBuffer, reader: SerialReader, log_path: str, cmd_log_path: str) -> None:
    global _buffer, _reader, _config, _log_path, _cmd_log_path
    _buffer = buffer
    _reader = reader
    _config = config
    _log_path = log_path
    _cmd_log_path = cmd_log_path


class Frame(BaseModel):
    t: float
    values: list[float]


class CommandRequest(BaseModel):
    values: list[float]


@app.get("/data", response_model=list[Frame])
def get_data(ms: int = Query(..., gt=0, description="Duration in milliseconds")):
    frames = _buffer.get_last_ms(ms)
    return [Frame(t=ts, values=vals) for ts, vals in frames]


@app.post("/command", status_code=204)
def send_command(body: CommandRequest):
    try:
        _reader.send_command(body.values)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/status")
def get_status():
    connected = _reader.ser is not None and _reader.ser.is_open
    return {
        "port": _config.port,
        "baud": _config.baud,
        "num_floats": _config.num_floats,
        "connected": connected,
        "buffer_frames": len(_buffer),
        "log_file": _log_path,
        "cmd_log_file": _cmd_log_path,
    }
