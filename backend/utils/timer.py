from time import perf_counter


class PerfTimer:
    def __init__(self) -> None:
        self._start = perf_counter()

    def elapsed_ms(self) -> float:
        return (perf_counter() - self._start) * 1000.0
