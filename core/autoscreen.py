from __future__ import annotations

import time
from typing import Callable


class AutoScreenError(RuntimeError):
    """Ошибка, связанная с автоматическим созданием скриншотов."""


def _press_with_pyautogui(key: str) -> None:
    """
    Отправляет нажатие клавиши через pyautogui.

    Args:
        key: Название клавиши (например, "f12").

    Raises:
        AutoScreenError: Если не удалось импортировать или использовать pyautogui.
    """
    try:
        import pyautogui
    except Exception as e:
        raise AutoScreenError(
            "Не удалось импортировать pyautogui. Установите пакет: pip install pyautogui"
        ) from e

    try:
        pyautogui.press(key)
    except Exception as e:
        raise AutoScreenError(f"Ошибка отправки клавиши {key}: {e}") from e


def press_hotkey(key: str = "f12", sender: Callable[[str], None] | None = None) -> None:
    """
    Отправляет глобальное нажатие клавиши.

    Args:
        key: Название клавиши (по умолчанию "f12").
        sender: Пользовательская функция отправки (для тестов). Если не указана,
            используется pyautogui.
    """
    (sender or _press_with_pyautogui)(key)


class AutoScreener:
    """
    Планировщик автоматических нажатий клавиши.

    Выполняет стартовую задержку, затем отправляет N нажатий с указанным интервалом.
    Управление происходит через метод tick(), который должен вызываться
    периодически (например, через QTimer в UI).

    Состояния:
        - idle: объект создан, но не запущен.
        - countdown: ожидание стартовой задержки.
        - running: выполняются нажатия.
        - done: все нажатия выполнены.
        - stopped: остановлен вручную.
    """

    def __init__(
            self,
            count: int,
            interval_sec: float,
            start_delay_sec: float,
            key: str = "f12",
            sender: Callable[[str], None] | None = None,
    ) -> None:
        """
        Args:
            count: Количество нажатий (должно быть > 0).
            interval_sec: Интервал между нажатиями в секундах (должен быть > 0).
            start_delay_sec: Задержка перед первым нажатием в секундах (>= 0).
            key: Клавиша для нажатия (по умолчанию "f12").
            sender: Пользовательская функция отправки (для тестов).
        """
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
        self._remaining: int = self.count
        self._state: str = "idle"

    @property
    def state(self) -> str:
        """Текущее состояние планировщика."""
        return self._state

    @property
    def remaining(self) -> int:
        """Количество оставшихся нажатий."""
        return max(0, self._remaining)

    def start(self, now: float | None = None) -> None:
        """
        Запускает планировщик.

        Args:
            now: Текущее время (для тестов). По умолчанию используется time.monotonic().
        """
        now = now if now is not None else time.monotonic()
        self._started_at = now
        self._next_fire = now + self.start_delay
        self._remaining = self.count
        self._state = "countdown" if self.start_delay > 0 else "running"

    def stop(self) -> None:
        """Останавливает планировщик."""
        self._state = "stopped"

    def seconds_to_next(self, now: float | None = None) -> float:
        """
        Возвращает время (в секундах) до следующего нажатия.

        Args:
            now: Текущее время (для тестов).

        Returns:
            float: Оставшееся время в секундах (неотрицательное).
        """
        if self._next_fire is None:
            return 0.0
        now = now if now is not None else time.monotonic()
        return max(0.0, self._next_fire - now)

    def tick(self, now: float | None = None) -> tuple[str, int, float]:
        """
        Выполняет шаг планировщика.

        Args:
            now: Текущее время (для тестов). По умолчанию используется time.monotonic().

        Returns:
            tuple[str, int, float]: (state, remaining, seconds_to_next)
                - state: текущее состояние.
                - remaining: оставшиеся нажатия.
                - seconds_to_next: время до следующего нажатия.
        """
        now = now if now is not None else time.monotonic()
        if self._state in ("done", "stopped", "idle"):
            return self._state, self.remaining, 0.0

        if self._state == "countdown" and now >= (self._next_fire or now):
            self._state = "running"

        if self._state == "running":
            while self._remaining > 0 and now >= (self._next_fire or now):
                press_hotkey(self.key, sender=self._sender)
                self._remaining -= 1
                self._next_fire = (self._next_fire or now) + self.interval

            if self._remaining == 0:
                self._state = "done"

        return self._state, self.remaining, self.seconds_to_next(now)
