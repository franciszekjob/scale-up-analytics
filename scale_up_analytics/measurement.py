from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

try:
    import psutil
except ImportError:  # pragma: no cover - exercised only without optional deps
    psutil = None

T = TypeVar("T")


@dataclass
class Measurement:
    value: T
    runtime_seconds: float
    peak_rss_bytes: int | None


class MemorySampler:
    def __init__(self, interval_seconds: float = 0.05) -> None:
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._peak_rss_bytes: int | None = None

    def __enter__(self) -> "MemorySampler":
        if psutil is None:
            return self

        process = psutil.Process()

        def sample() -> None:
            peak = 0
            while not self._stop_event.is_set():
                try:
                    rss = process.memory_info().rss
                    for child in process.children(recursive=True):
                        try:
                            rss += child.memory_info().rss
                        except psutil.Error:
                            continue
                    peak = max(peak, rss)
                except psutil.Error:
                    pass
                time.sleep(self.interval_seconds)
            self._peak_rss_bytes = peak or self._peak_rss_bytes

        self._thread = threading.Thread(target=sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join()

    @property
    def peak_rss_bytes(self) -> int | None:
        return self._peak_rss_bytes


def measure(callable_obj: Callable[[], T]) -> Measurement[T]:
    started_at = time.perf_counter()
    with MemorySampler() as sampler:
        value = callable_obj()
    runtime_seconds = time.perf_counter() - started_at
    return Measurement(
        value=value,
        runtime_seconds=runtime_seconds,
        peak_rss_bytes=sampler.peak_rss_bytes,
    )
