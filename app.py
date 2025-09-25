"""Точка входа для приложения Steam Screenshot Rebinder."""

import sys
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> int:
    """Запускает приложение.

    Returns:
        int: Код завершения приложения.
    """
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
