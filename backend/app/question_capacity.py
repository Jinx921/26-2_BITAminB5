from threading import Lock


class QuestionExecutionGate:
    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._active = 0
        self._lock = Lock()

    def try_enter(self) -> bool:
        with self._lock:
            if self._active >= self._capacity:
                return False
            self._active += 1
            return True

    def leave(self) -> None:
        with self._lock:
            if self._active <= 0:
                raise RuntimeError("question execution gate released without entry")
            self._active -= 1
