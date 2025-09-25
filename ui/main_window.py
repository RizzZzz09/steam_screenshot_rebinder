from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QFileDialog,
    QLabel, QTextEdit, QCheckBox, QComboBox, QSpinBox, QMessageBox, QProgressBar
)

from core.scanner import scan_old_new
from core.mapping import build_pairs, preview_pairs, get_image_info
from core.replacer import replace_many
from core.autoscreen import AutoScreener, AutoScreenError


class MainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Steam Screenshot Rebinder — light UI")
        self.setMinimumWidth(900)

        # --- Paths row
        self.old_edit = QLineEdit()
        self.old_btn = QPushButton("Выбрать OLD…")
        self.old_btn.clicked.connect(self.choose_old)

        self.new_edit = QLineEdit()
        self.new_btn = QPushButton("Выбрать NEW…")
        self.new_btn.clicked.connect(self.choose_new)

        paths_layout = QVBoxLayout()
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Папка OLD:"))
        row1.addWidget(self.old_edit, 1)
        row1.addWidget(self.old_btn)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Папка NEW (screenshots):"))
        row2.addWidget(self.new_edit, 1)
        row2.addWidget(self.new_btn)
        paths_layout.addLayout(row1)
        paths_layout.addLayout(row2)

        # --- Options
        self.dry_chk = QCheckBox("Dry-run")
        self.dry_chk.setChecked(True)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["auto", "jpg", "png"])

        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 2000)
        self.limit_spin.setValue(20)

        opts_layout = QHBoxLayout()
        opts_layout.addWidget(QLabel("Формат:"))
        opts_layout.addWidget(self.format_combo)
        opts_layout.addSpacing(16)
        opts_layout.addWidget(QLabel("Предпросмотр (строк):"))
        opts_layout.addWidget(self.limit_spin)
        opts_layout.addStretch()
        opts_layout.addWidget(self.dry_chk)

        # --- Actions
        self.preview_btn = QPushButton("Предпросмотр пар")
        self.preview_btn.clicked.connect(self.on_preview)

        self.replace_btn = QPushButton("Заменить содержимое")
        self.replace_btn.clicked.connect(self.on_replace)
        self.replace_btn.setEnabled(False)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.preview_btn)
        actions_layout.addWidget(self.replace_btn)
        actions_layout.addStretch()

        # --- AutoScreen (F12)
        self.autoscreen_count = QSpinBox()
        self.autoscreen_count.setRange(1, 100000)
        self.autoscreen_count.setValue(10)

        self.autoscreen_interval = QSpinBox()
        self.autoscreen_interval.setRange(1, 3600)
        self.autoscreen_interval.setValue(2)
        self.autoscreen_interval.setSuffix(" сек")

        self.autoscreen_delay = QSpinBox()
        self.autoscreen_delay.setRange(0, 3600)
        self.autoscreen_delay.setValue(5)
        self.autoscreen_delay.setSuffix(" сек")

        self.autoscreen_status = QLabel("Автоскрин: не запущен")
        self.autoscreen_start_btn = QPushButton("Старт F12")
        self.autoscreen_stop_btn = QPushButton("Стоп")
        self.autoscreen_stop_btn.setEnabled(False)

        self.autoscreen_start_btn.clicked.connect(self.on_autoscreen_start)
        self.autoscreen_stop_btn.clicked.connect(self.on_autoscreen_stop)

        autos_layout = QHBoxLayout()
        autos_layout.addWidget(QLabel("Автоскрин (F12):"))
        autos_layout.addSpacing(8)
        autos_layout.addWidget(QLabel("Кол-во:"))
        autos_layout.addWidget(self.autoscreen_count)
        autos_layout.addSpacing(8)
        autos_layout.addWidget(QLabel("Интервал:"))
        autos_layout.addWidget(self.autoscreen_interval)
        autos_layout.addSpacing(8)
        autos_layout.addWidget(QLabel("Задержка старта:"))
        autos_layout.addWidget(self.autoscreen_delay)
        autos_layout.addSpacing(8)
        autos_layout.addWidget(self.autoscreen_start_btn)
        autos_layout.addWidget(self.autoscreen_stop_btn)
        autos_layout.addStretch()
        autos_layout.addWidget(self.autoscreen_status)

        # --- Progress + Log
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        # --- Root layout
        root = QVBoxLayout(self)
        root.addLayout(paths_layout)
        root.addLayout(opts_layout)
        root.addLayout(actions_layout)
        root.addLayout(autos_layout)
        root.addWidget(self.progress)
        root.addWidget(QLabel("Лог:"))
        root.addWidget(self.log, 1)

        # State
        self._old_dir: Path | None = None
        self._new_dir: Path | None = None
        self._replace_queue: list[tuple[Path, Path]] = []
        self._replace_index = 0

        # AutoScreen state
        self._autos_timer = QTimer(self)
        self._autos_timer.setInterval(100)  # 10 тиков/сек
        self._autos_timer.timeout.connect(self._autos_tick)
        self._autos_runner: AutoScreener | None = None
        self._autos_prev_remaining: int | None = None
        self._autos_prev_countdown_sec: int | None = None

    # --------------------------- Log helpers ---------------------------

    def _log_clear(self):
        self.log.clear()
        self.log.setAcceptRichText(True)

    def _log_html(self, html: str):
        self.log.append(html)
        self.log.ensureCursorVisible()

    def _badge(self, text: str, color: str) -> str:
        return (
            '<span style="display:inline-block;padding:1px 6px;'
            f'border-radius:6px;background:{color};color:#fff;'
            'font:11px/1.4 monospace;">' + text + '</span>'
        )

    def _sep(self):
        self._log_html('<div style="margin:6px 0;border-top:1px solid #3a3a3a;"></div>')

    def _mono(self, s: str) -> str:
        return f'<span style="font-family:ui-monospace,Consolas,monospace">{s}</span>'

    def _fmt_pair_preview(self, idx: int, old_name: str, old_wh: str, old_fmt: str,
                          new_name: str, new_wh: str, new_fmt: str) -> str:
        left = self._mono(f"{idx:>3}.  OLD: {old_name:<32}  {old_wh:<12} {old_fmt:<5}")
        right = self._mono(f"NEW: {new_name:<32}  {new_wh:<12} {new_fmt:<5}")
        return f'<div style="margin:2px 0">{left}<br>{right}</div>'

    def _fmt_result(self, ok: bool, new_name: str, old_name: str, action: str, err: str | None) -> str:
        badge = self._badge("OK", "#2e7d32") if ok else self._badge("ERR", "#c62828")
        mid = '&larr;'
        if ok:
            tail = self._mono(f"({action})")
        else:
            tail = f'<span style="color:#ffb4a9">{self._mono(err or "unknown error")}</span>'
        line = f'{badge} {self._mono(new_name)} {mid} {self._mono(old_name)}  {tail}'
        return f'<div style="margin:2px 0">{line}</div>'

    # --------------------------- Path helpers ---------------------------

    def choose_old(self):
        d = QFileDialog.getExistingDirectory(self, "Выбери папку OLD")
        if d:
            self.old_edit.setText(d)
            self._old_dir = Path(d)

    def choose_new(self):
        d = QFileDialog.getExistingDirectory(self, "Выбери папку NEW (screenshots)")
        if d:
            self.new_edit.setText(d)
            self._new_dir = Path(d)

    def _get_paths(self):
        old = self._old_dir or Path(self.old_edit.text().strip('"'))
        new = self._new_dir or Path(self.new_edit.text().strip('"'))
        if not old.is_dir():
            QMessageBox.warning(self, "Ошибка", "Папка OLD не найдена.")
            return None
        if not new.is_dir():
            QMessageBox.warning(self, "Ошибка", "Папка NEW не найдена.")
            return None
        return old, new

    def _set_busy(self, busy: bool):
        self.preview_btn.setEnabled(not busy)
        self.replace_btn.setEnabled(not busy and bool(self._replace_queue))
        self.old_btn.setEnabled(not busy)
        self.new_btn.setEnabled(not busy)
        self.format_combo.setEnabled(not busy)
        self.limit_spin.setEnabled(not busy)
        self.dry_chk.setEnabled(not busy)
        self.setCursor(Qt.BusyCursor if busy else Qt.ArrowCursor)

    # --------------------------- Preview flow ---------------------------

    def on_preview(self):
        paths = self._get_paths()
        if not paths:
            return
        old, new = paths
        self._log_clear()
        self._log_html("<h4>▶ Предпросмотр пар</h4>")
        self._sep()
        self._set_busy(True)
        self.progress.setValue(0)
        try:
            old_list, new_list, scan_warnings = scan_old_new(old, new)
            pairs, map_warnings = build_pairs(old_list, new_list)
            show_n = min(self.limit_spin.value(), len(pairs))
            for i in range(show_n):
                p = pairs[i]
                try:
                    oi = get_image_info(p.old)
                    ni = get_image_info(p.new)
                    line = self._fmt_pair_preview(
                        i + 1, p.old.name, f"{oi.width}x{oi.height}", oi.fmt or "?",
                        p.new.name, f"{ni.width}x{ni.height}", ni.fmt or "?"
                    )
                except Exception as e:
                    line = (
                        f'<div style="color:#ffb74d">'
                        f'{self._mono(f"{i+1:>3}. {p.new.name} ← {p.old.name}")}'
                        f' — ошибка чтения: {e}</div>'
                    )
                self._log_html(line)

            self._sep()
            warns = [*scan_warnings, *map_warnings]
            if warns:
                self._log_html('<div><b>⚠ Предупреждения:</b></div>')
                for w in warns:
                    self._log_html(f'<div style="color:#ffb74d">• {w}</div>')

            self._log_html(
                f'<div style="margin-top:6px">'
                f'{self._mono(f"Итого пар: {len(pairs)} (OLD={len(old_list)}, NEW={len(new_list)})")}'
                f'</div>'
            )
            self._replace_queue = [(p.old, p.new) for p in pairs]
            self.replace_btn.setEnabled(len(pairs) > 0)
        except Exception as e:
            self._log_html(f'<div style="color:#ef9a9a">❌ Ошибка предпросмотра: {e}</div>')
        finally:
            self.progress.setValue(0)
            self._set_busy(False)

    # --------------------------- Replace flow ---------------------------

    def on_replace(self):
        if not self._replace_queue:
            QMessageBox.information(self, "Нет пар", "Сначала сделай предпросмотр.")
            return

        dry = self.dry_chk.isChecked()
        ff = self.format_combo.currentText()
        force_format = None if ff == "auto" else ff

        self._log_clear()
        self._log_html(
            f'<h4>▶ Замена содержимого</h4>'
            f'<div style="margin-bottom:4px">{self._badge("dry-run: ON" if dry else "dry-run: OFF", "#546e7a")} '
            f'{self._badge(f"format: {ff}", "#37474f")}</div>'
        )
        self._sep()

        self._replace_queue = [(o, n, dry, force_format) for (o, n) in self._replace_queue]
        self._replace_index = 0

        self._set_busy(True)
        self.progress.setValue(0)
        QTimer.singleShot(0, self._process_next_replace)

    def _process_next_replace(self):
        total = len(self._replace_queue)

        if self._replace_index >= total:
            self._sep()
            self._log_html(self._mono(f"Готово: {total}/{total}"))
            self._set_busy(False)
            return

        old_p, new_p, dry, force_format = self._replace_queue[self._replace_index]
        try:
            res = replace_many([(old_p, new_p)], dry_run=dry, force_format=force_format)[0]
            html = self._fmt_result(res.ok, new_p.name, old_p.name, res.action, res.error)
            self._log_html(html)
        except Exception as e:
            self._log_html(self._fmt_result(False, new_p.name, old_p.name, "error", str(e)))

        self._replace_index += 1
        self.progress.setValue(int(self._replace_index * 100 / max(1, total)))
        QTimer.singleShot(0, self._process_next_replace)

    # --------------------------- AutoScreen (F12) ---------------------------

    def on_autoscreen_start(self):
        if self._autos_runner is not None:
            QMessageBox.information(self, "Уже запущено", "Автоскрин уже выполняется.")
            return

        count = self.autoscreen_count.value()
        interval = self.autoscreen_interval.value()
        delay = self.autoscreen_delay.value()

        if delay < 2:
            reply = QMessageBox.question(
                self, "Внимание",
                "Задержка запуска меньше 2 секунд. Успеешь переключиться в игру?\n"
                "Продолжить?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        try:
            self._autos_runner = AutoScreener(
                count=count, interval_sec=float(interval),
                start_delay_sec=float(delay), key="f12"
            )
            self._autos_runner.start()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить автоскрин: {e}")
            self._autos_runner = None
            return

        # лог-баннер
        self._log_html("<h4>▶ Автоскрин (F12)</h4>")
        self._sep()

        # сброс счётчиков для логики тиков
        self._autos_prev_remaining = self._autos_runner.remaining
        self._autos_prev_countdown_sec = None

        self.autoscreen_status.setText(f"Старт через: {int(delay)}s")
        self.autoscreen_start_btn.setEnabled(False)
        self.autoscreen_stop_btn.setEnabled(True)
        self._autos_timer.start()

    def on_autoscreen_stop(self):
        if self._autos_runner is not None:
            self._autos_runner.stop()
        self._autos_timer.stop()
        self._autos_runner = None
        self.autoscreen_status.setText("Автоскрин: остановлен")
        self.autoscreen_start_btn.setEnabled(True)
        self.autoscreen_stop_btn.setEnabled(False)
        self._autos_prev_remaining = None
        self._autos_prev_countdown_sec = None

    def _autos_tick(self):
        if self._autos_runner is None:
            self._autos_timer.stop()
            self.autoscreen_status.setText("Автоскрин: не запущен")
            self.autoscreen_start_btn.setEnabled(True)
            self.autoscreen_stop_btn.setEnabled(False)
            return

        try:
            state, remaining, sec_to_next = self._autos_runner.tick()
        except AutoScreenError as e:
            self._autos_timer.stop()
            self._autos_runner = None
            self.autoscreen_status.setText(f"Ошибка автоскрина: {e}")
            self.autoscreen_start_btn.setEnabled(True)
            self.autoscreen_stop_btn.setEnabled(False)
            QMessageBox.critical(self, "Ошибка автоскрина", str(e))
            return
        except Exception as e:
            self._autos_timer.stop()
            self._autos_runner = None
            self.autoscreen_status.setText(f"Неожиданная ошибка: {e}")
            self.autoscreen_start_btn.setEnabled(True)
            self.autoscreen_stop_btn.setEnabled(False)
            QMessageBox.critical(self, "Ошибка автоскрина", str(e))
            return

        # Countdown: показываем только целые секунды
        if state == "countdown":
            left_sec = int(max(0, round(sec_to_next)))
            if self._autos_prev_countdown_sec != left_sec:
                self.autoscreen_status.setText(f"Старт через: {left_sec}s")
                self._autos_prev_countdown_sec = left_sec
            return

        # Running: если уменьшилось remaining -> было нажатие F12
        if state == "running":
            if self._autos_prev_remaining is None:
                self._autos_prev_remaining = remaining

            if remaining < self._autos_prev_remaining:
                # Было одно или несколько нажатий
                done = self._autos_prev_remaining - remaining
                from datetime import datetime
                for k in range(done):
                    idx = (self._autos_runner.count - (self._autos_prev_remaining - k) + 1)
                    t = datetime.now().strftime("%H:%M:%S")
                    self._log_html(self._mono(f"[{t}] [F12] скрин #{idx}"))
                self._autos_prev_remaining = remaining

            self.autoscreen_status.setText(f"Идёт автоскрин — осталось: {remaining}")
            return

        # Завершено/остановлено
        if state in ("done", "stopped"):
            total = self._autos_runner.count
            made = total - remaining
            self._sep()
            self._log_html(self._mono(f"Автоскрин завершён: {made}/{total} сделано"))
            self._autos_timer.stop()
            self._autos_runner = None
            self.autoscreen_status.setText("Автоскрин: завершён" if state == "done" else "Автоскрин: остановлен")
            self.autoscreen_start_btn.setEnabled(True)
            self.autoscreen_stop_btn.setEnabled(False)
            self._autos_prev_remaining = None
            self._autos_prev_countdown_sec = None
