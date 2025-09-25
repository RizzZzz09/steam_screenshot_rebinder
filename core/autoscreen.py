# core/autoscreen.py
from __future__ import annotations

import time
from typing import Callable


class AutoScreenError(RuntimeError):
    pass


def _press_with_pyautogui(key: str) -> None:
    try:
        import pyautogui
    except Exception as e:
        raise AutoScreenError(
            "Не удалось импортировать pyautogui. Установите пакет: pip install pyautogui"
        ) from e
    # без искусственных пауз
    try:
        # pyautogui.FAILSAFE = False  # можно включить при желании
        pyautogui.press(key)
    except Exception as e:
        raise AutoScreenError(f"Ошибка отправки клавиши {key}: {e}") from e


def press_hotkey(key: str = "f12", sender: Callable[[str], None] | None = None) -> None:
    """
    Отправляет глобальное нажатие клавиши (по умолчанию F12).
    По умолчанию использует pyautogui. Можно передать sender(key) для тестов.
    """
    (sender or _press_with_pyautogui)(key)


class AutoScreener:
    """
    Лёгкий планировщик: стартовая задержка, затем N нажатий с интервалом.
    Управление — методом tick(now), который возвращает текущую стадию и остаток.
    Без потоков (используем QTimer в UI).
    """

    def __init__(self, count: int, interval_sec: float, start_delay_sec: float, key: str = "f12",
                 sender: Callable[[str], None] | None = None):
        if count <= 0:
            raise ValueError("count должен быть > 0")
        if interval_sec <= 0:
            raise ValueError("interval_sec должен быть > 0")
        if start_delay_sec < 0:
            raise ValueError("start_delay_sec должен быть >= 0")

        self.count = int(count)
        self.interval = float(interval_sec)
        self.start_delay = float(start_delay_sec)
        self.key = key
        self._sender = sender

        self._started_at: float | None = None
        self._next_fire: float | None = None
        self._remaining = self.count
        self._state = "idle"  # idle | countdown | running | done | stopped

    @property
    def state(self) -> str:
        return self._state

    @property
    def remaining(self) -> int:
        return max(0, self._remaining)

    def start(self, now: float | None = None) -> None:
        now = now if now is not None else time.monotonic()
        self._started_at = now
        self._next_fire = now + self.start_delay
        self._remaining = self.count
        self._state = "countdown" if self.start_delay > 0 else "running"

    def stop(self) -> None:
        self._state = "stopped"

    def seconds_to_next(self, now: float | None = None) -> float:
        if self._next_fire is None:
            return 0.0
        now = now if now is not None else time.monotonic()
        return max(0.0, self._next_fire - now)

    def tick(self, now: float | None = None) -> tuple[str, int, float]:
        """
        Возвращает (state, remaining, seconds_to_next).
        При переходе таймера — отправляет нажатие клавиши.
        """
        now = now if now is not None else time.monotonic()
        if self._state in ("done", "stopped", "idle"):
            return self._state, self.remaining, 0.0

        # переход из countdown в running
        if self._state == "countdown":
            if now >= (self._next_fire or now):
                self._state = "running"

        if self._state == "running":
            # может потребоваться несколько «шагов», если тики редкие
            while self._remaining > 0 and now >= (self._next_fire or now):
                press_hotkey(self.key, sender=self._sender)
                self._remaining -= 1
                self._next_fire = (self._next_fire or now) + self.interval
            if self._remaining == 0:
                self._state = "done"

        return self._state, self.remaining, self.seconds_to_next(now)
