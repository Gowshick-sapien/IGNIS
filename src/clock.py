import time

class Clock:
    def time(self) -> float:
        return time.time()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def strftime(self, format: str, t = None) -> str:
        if t is None:
            t = self.time()
        if isinstance(t, (time.struct_time, tuple)):
            return time.strftime(format, t)
        return time.strftime(format, time.gmtime(t))

class MockClock:
    def __init__(self, start_time: float = 0.0):
        self._current_time = start_time
        self.sleeps = []

    def time(self) -> float:
        return self._current_time

    def sleep(self, seconds: float) -> None:
        self._current_time += seconds
        self.sleeps.append(seconds)

    def advance(self, seconds: float) -> None:
        self._current_time += seconds

    def strftime(self, format: str, t = None) -> str:
        if t is None:
            t = self.time()
        if isinstance(t, (time.struct_time, tuple)):
            return time.strftime(format, t)
        return time.strftime(format, time.gmtime(t))

default_clock = Clock()
