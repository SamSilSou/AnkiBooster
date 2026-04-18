#!/usr/bin/env python3
"""
🚀 Anki Booster - Tray Manager (v0.4)
Gerencia ícone, menu, animação GIF e retry de boot.
Emite sinais para o service executar ações.
✅ Thread-safe, compatível com Wayland, fallback elegante.
"""
import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QIcon, QMovie, QPixmap

from booster_utils import log, SCRIPT_DIR


class BoosterTray(QObject):
    # Sinais emitidos para o service principal (conectar no App.__init__)
    start_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()
    toggle_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.tray_icon = None
        self.tray_menu = None
        self.tray_movie = None
        self._tray_attempts = 0
        self._is_running = False
        self._is_paused = False

        # Delay inicial para contornar race condition de boot (Wayland/systemd)
        QTimer.singleShot(2000, self._try_init)

    def _try_init(self):
        """Tenta inicializar a tray com retry automático"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            gif_path = os.path.join(SCRIPT_DIR, "rocket.gif")
            icon = self._load_icon(gif_path)

            self.tray_icon = QSystemTrayIcon(icon)
            self.tray_icon.setToolTip("Anki Booster 🚀")
            self.tray_icon.activated.connect(self._on_activated)
            
            self.tray_menu = QMenu()
            self.tray_icon.setContextMenu(self.tray_menu)
            self._build_menu()
            self.tray_icon.show()
            log("📍 Ícone de tray ativado", "OK")
        else:
            self._tray_attempts += 1
            if self._tray_attempts <= 6:
                log(f"⏳ Tray não pronto, tentando novamente ({self._tray_attempts}/6)...", "INFO")
                QTimer.singleShot(2000, self._try_init)
            else:
                log("⚠️ Tray indisponível. Controle via TCP.", "WARN")

    def _load_icon(self, gif_path):
        """Carrega GIF animado ou fallback estático"""
        if os.path.exists(gif_path):
            self.tray_movie = QMovie(gif_path)
            if self.tray_movie.isValid():
                self.tray_movie.frameChanged.connect(self._on_frame_changed)
                self.tray_movie.start()
                return self._current_icon()
        self.tray_movie = None
        return self._fallback_icon()

    def _current_icon(self):
        """Extrai frame atual do GIF redimensionado para tray"""
        if self.tray_movie and self.tray_movie.isValid():
            pm = self.tray_movie.currentPixmap().scaled(
                24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            return QIcon(pm)
        return self._fallback_icon()

    def _fallback_icon(self):
        """Ícone estático de fallback"""
        icon_path = os.path.join(SCRIPT_DIR, "icon.svg")
        return QIcon(icon_path) if os.path.exists(icon_path) else QIcon.fromTheme("anki", QIcon.fromTheme("system-run"))

    def _on_frame_changed(self):
        """Atualiza ícone a cada frame do GIF (thread-safe via Qt)"""
        if self.tray_icon:
            self.tray_icon.setIcon(self._current_icon())

    def _on_activated(self, reason):
        """Duplo clique → toggle janela"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window_requested.emit()

    def _build_menu(self):
        """Reconstroi menu conforme estado atual (chamado via QTimer para thread-safety)"""
        if not self.tray_menu:
            return
        self.tray_menu.clear()

        if not self._is_running:
            action = self.tray_menu.addAction("▶️ Iniciar Booster")
            action.triggered.connect(self.start_requested.emit)
        else:
            label = "⏸️ Pausar" if not self._is_paused else "▶️ Retomar"
            action = self.tray_menu.addAction(label)
            if self._is_paused:
                action.triggered.connect(self.resume_requested.emit)
            else:
                action.triggered.connect(self.pause_requested.emit)

        self.tray_menu.addSeparator()
        quit_action = self.tray_menu.addAction("🚪 Sair")
        quit_action.triggered.connect(self.quit_requested.emit)

    # ───────── Métodos públicos para o service atualizar estado (thread-safe) ─────────
    def set_running(self, is_running: bool):
        """Chamar após Booster iniciar (thread-safe via QTimer)"""
        self._is_running = is_running
        self._refresh()

    def set_paused(self, is_paused: bool):
        """Chamar ao pausar/retomar (thread-safe via QTimer)"""
        self._is_paused = is_paused
        self._refresh()

    def _refresh(self):
        """Agenda rebuild do menu no event loop principal → seguro para chamar de TCP threads"""
        QTimer.singleShot(0, self._build_menu)