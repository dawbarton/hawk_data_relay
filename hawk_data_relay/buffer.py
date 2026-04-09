import threading
import time
from collections import deque


class RingBuffer:
    def __init__(self, maxlen: int = 50000):
        self._buf: deque[tuple[float, list[float]]] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def push(self, timestamp: float, values: list[float]) -> None:
        with self._lock:
            self._buf.append((timestamp, values))

    def get_last_ms(self, ms: int) -> list[tuple[float, list[float]]]:
        cutoff = time.time() - ms / 1000.0
        with self._lock:
            return [(ts, vals) for ts, vals in self._buf if ts >= cutoff]

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)
