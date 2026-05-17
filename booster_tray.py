#!/usr/bin/env python3
"""
🚀 Anki Booster - Tray Manager (v0.4.2)
"""
from __future__ import annotations
import webbrowser
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt, QSize
from PyQt6.QtGui import QIcon, QMovie, QPixmap, QKeySequence, QAction
from booster_utils import log, SCRIPT_DIR

class BoosterTray(QObject):
    # ───────── Sinais para o service principal ─────────
    start_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()
    toggle_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    logs_requested = pyqtSignal()  # 🎤 NOVO: abrir interface de logs

    RETRY_DELAY_MS = 2000
    MAX_RETRIES = 6
    ICON_SIZE = QSize(24, 24)
    TOOLTIP_BASE = "Anki Booster 🚀"

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._tray_menu: Optional[QMenu] = None
        self._tray_movie: Optional[QMovie] = None
        self._retry_count = 0
        self._is_running = False
        self._is_paused = False
        self._icon_cache: Optional[QIcon] = None
        self._last_frame = -1
        QTimer.singleShot(self.RETRY_DELAY_MS, self._try_init)

    def _try_init(self) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            if self._setup_tray():
                log("📍 Tray inicializada com sucesso", "OK")
                return
        self._retry_count += 1
        if self._retry_count <= self.MAX_RETRIES:
            log(f"⏳ Tray não pronta ({self._retry_count}/{self.MAX_RETRIES}), retry...", "INFO")
            QTimer.singleShot(self.RETRY_DELAY_MS, self._try_init)
        else:
            log("⚠️ Tray indisponível. Controle via TCP.", "WARN")

    def _setup_tray(self) -> bool:
        try:
            icon = self._load_animated_icon()
            self._tray_icon = QSystemTrayIcon(icon)
            self._tray_icon.setToolTip(self.TOOLTIP_BASE)
            self._tray_icon.activated.connect(self._on_activated)
            self._tray_menu = QMenu()
            self._tray_icon.setContextMenu(self._tray_menu)
            self._build_menu()
            self._tray_icon.show()
            return True
        except Exception as e:
            log(f"❌ Erro ao configurar tray: {e}", "ERR")
            return False

    def _load_animated_icon(self) -> QIcon:
        gif_path = Path(SCRIPT_DIR) / "rocket.gif"
        if gif_path.exists():
            self._tray_movie = QMovie(str(gif_path))
            if self._tray_movie.isValid():
                self._tray_movie.frameChanged.connect(self._on_frame_changed)
                self._tray_movie.start()
                return self._get_cached_icon()
        self._tray_movie = None
        return self._get_static_icon()

    def _get_cached_icon(self) -> QIcon:
        if self._icon_cache and self._tray_movie and self._tray_movie.currentFrameNumber() == self._last_frame:
            return self._icon_cache
        self._last_frame = self._tray_movie.currentFrameNumber() if self._tray_movie else -1
        self._icon_cache = self._scale_icon(self._tray_movie.currentPixmap() if self._tray_movie else None)
        return self._icon_cache

    def _scale_icon(self, pixmap: Optional[QPixmap]) -> QIcon:
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(self.ICON_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            return QIcon(scaled)
        return self._get_static_icon()

    def _get_static_icon(self) -> QIcon:
        icon_path = Path(SCRIPT_DIR) / "icon.svg"
        if icon_path.exists():
            return QIcon(str(icon_path))
        for theme_name in ["anki", "system-run", "applications-education"]:
            icon = QIcon.fromTheme(theme_name)
            if not icon.isNull():
                return icon
        return QIcon.fromTheme("application-x-executable")

    def _on_frame_changed(self) -> None:
        if self._tray_icon:
            self._tray_icon.setIcon(self._get_cached_icon())
            status = "⏸️" if self._is_paused else "▶️" if self._is_running else "⏹️"
            self._tray_icon.setToolTip(f"{self.TOOLTIP_BASE} {status}")

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window_requested.emit()

    def _build_menu(self) -> None:
        if not self._tray_menu:
            return
        self._tray_menu.clear()
        if not self._is_running:
            self._add_action("▶️ Iniciar Booster", self.start_requested.emit, "Ctrl+Shift+S")
        else:
            label = "▶️ Retomar" if self._is_paused else "⏸️ Pausar"
            slot = self.resume_requested.emit if self._is_paused else self.pause_requested.emit
            self._add_action(label, slot, "Ctrl+Shift+P")
        #self._tray_menu.addSeparator()
        
        self._add_action("📕 Ver Logs", self._open_logs, "Ctrl+Shift+L", is_dangerous=False)
            
        # self._tray_menu.addSeparator()
        self._add_action("🔄 Reload", self.quit_requested.emit, "Ctrl+Q", is_dangerous=True)

    def _add_action(self, text: str, slot, shortcut: Optional[str] = None, is_dangerous: bool = False) -> QAction:
        action = QAction(text, self._tray_menu)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
            action.setToolTip(f"{text} ({shortcut})")
        if is_dangerous:
            action.setIcon(QIcon.fromTheme("application-exit"))
        self._tray_menu.addAction(action)
        return action

    def set_running(self, is_running: bool) -> None:
        if self._is_running == is_running: return
        self._is_running = is_running
        self._refresh_menu()

    def set_paused(self, is_paused: bool) -> None:
        if self._is_paused == is_paused: return
        self._is_paused = is_paused
        self._refresh_menu()

    def _refresh_menu(self) -> None:
        QTimer.singleShot(0, self._build_menu)
        
    def _open_logs(self):
        """Abre a interface de logs no navegador padrão"""
        url = "http://127.0.0.1:8895/"
        try:
            webbrowser.open(url, new=2)
        except:
            # Fallback mínimo por SO
            import os, sys
            if sys.platform == "linux": os.system(f"xdg-open {url} &")
            elif sys.platform == "win32": os.system(f"start {url}")
            elif sys.platform == "darwin": os.system(f"open {url}")

    def cleanup(self) -> None:
        if self._tray_movie and self._tray_movie.state() == QMovie.MovieState.Running:
            self._tray_movie.stop()
        if self._tray_icon:
            self._tray_icon.hide()
            self._tray_icon = None
        log("🧹 Tray limpa", "INFO")
