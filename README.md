# hawk-data-relay

A serial-to-HTTP bridge for MCU experiment data. Continuously records data from a microcontroller over a serial port, buffers it in memory, and exposes a local HTTP API so MATLAB can pull recent data and send commands.

## Data format

The MCU communicates using [PacketSerial](https://github.com/bakercp/PacketSerial) (COBS framing): each packet is COBS-encoded and terminated with a `0x00` byte. Both incoming data and outgoing commands are arrays of `float32` values packed in little-endian order.

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
# Windows
python -m hawk_data_relay --port COM3 --baud 460800 --num-floats 10

# macOS / Linux
python -m hawk_data_relay --port /dev/tty.usbserial-0001 --baud 460800 --num-floats 10
```

### All options

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | *(required)* | Serial port name |
| `--baud` | `460800` | Baud rate |
| `--num-floats` | `10` | Number of `float32` values per data frame |
| `--host` | `127.0.0.1` | API listen address |
| `--api-port` | `5000` | API listen port |
| `--log-dir` | `./logs` | Directory for CSV log files |
| `--buffer-maxlen` | `50000` | Maximum frames held in memory |
| `--log-level` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## HTTP API

Interactive API docs are available at `http://localhost:5000/docs` once the relay is running.

### `GET /data?ms=<milliseconds>`

Returns the last N milliseconds of buffered data as a JSON array.

```
GET http://localhost:5000/data?ms=5000
```

```json
[
  {"t": 1712600123.450, "values": [1.0, 2.0, 3.0, ...]},
  {"t": 1712600123.460, "values": [1.1, 2.1, 3.1, ...]},
  ...
]
```

### `POST /command`

Sends a command to the MCU as a COBS-encoded `float32` array (same framing as received data).

```json
{"values": [1.0, 0.5, 0.0]}
```

Returns `204 No Content` on success, `503` if the serial port is not connected.

### `GET /status`

Returns the current state of the relay.

```json
{
  "port": "COM3",
  "baud": 460800,
  "num_floats": 10,
  "connected": true,
  "buffer_frames": 1234,
  "log_file": "logs/experiment_20240409_143022.csv"
}
```

## Log files

Each run creates a timestamped CSV in `--log-dir`:

```
logs/experiment_20240409_143022.csv
```

Format: one row per frame, first column is a Unix timestamp.

```
# timestamp,ch0,ch1,ch2,...
1712600123.450000,1.000000,2.000000,...
```

Load in MATLAB after the experiment:

```matlab
data = readmatrix('logs/experiment_20240409_143022.csv', 'CommentStyle', '#');
timestamps = data(:, 1);
channels   = data(:, 2:end);
```

## MATLAB usage

Helper functions are provided in the `matlab/` directory. Add it to your MATLAB path:

```matlab
addpath('path/to/hawk-data-relay/matlab')
```

### `hawk_receive(ms)` → `[data, timestamps]`

```matlab
% Pull last 5 seconds of data
[data, timestamps] = hawk_receive(5000);
% data       — N × num_floats double matrix
% timestamps — N × 1 Unix timestamp vector
```

### `hawk_send(values)`

```matlab
% Send a command (float32 array, COBS-encoded, same framing as received data)
hawk_send([1.0, 0.5, 0.0]);
```

Both functions accept an optional second argument to override the relay URL (default `http://localhost:5000`).

### Check relay status

```matlab
status = webread('http://localhost:5000/status');
disp(status.connected)
```
