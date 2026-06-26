from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter


@dataclass
class Timer:
    started_at: float
    elapsed_ms: int = 0


@contextmanager
def measure_time() -> Generator[Timer, None, None]:
    timer = Timer(started_at=perf_counter())
    try:
        yield timer
    finally:
        timer.elapsed_ms = max(0, round((perf_counter() - timer.started_at) * 1000))
