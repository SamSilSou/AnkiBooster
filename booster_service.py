#!/usr/bin/env python3
"""
🚀 Anki Booster - Serviço Principal
Lógica de UI, TCP, loop e processamento de cards.
"""
import sys, os, time, socket, datetime, json, threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl, QTimer, QSize, Qt

# Imports dos utilitários
from booster_utils import (
    # Paths e config
    SCRIPT_DIR, BOOSTER_DATA_DIR, STATE_FILE, DAILY_FILE, CONFIG_FILE, CMD_PORT,
    DEFAULT_CONFIG, load_config, load_json_file, save_json_file,
    # Log e DB
    log, get_all_favs, toggle_fav, graduate_fav, is_anki_closed,
    # HTML e mídia
    _wrap_html, _get_fav_level_max,
    # Card loader
    load_cards_from_anki
)

# ───────────────── CONSTANTES DE MÓDULO ─────────────────
VALID_CONFIG_KEYS = set(DEFAULT_CONFIG.keys())

# ───────────────── VARIÁVEIS GLOBAIS DE CONFIG ─────────────────
LIMIT_CARDS = GLOBAL_CORRECT = GLOBAL_WRONG = MAX_DAILY = BUFFER_SIZE = None
FAVS_PRIORITY = REVLOG_DAYS = REVLOG_TYPES = FAV_BONUS = None
FAV_LEVELS = {1: 6, 2: 4, 3: 2}

# ───────────────── PONTE PYTHON ↔ QML ─────────────────
class Bridge(QObject):
    """Ponte de comunicação entre Python backend e QML frontend"""
    show = pyqtSignal(str)
    hide = pyqtSignal()
    
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.pending_callback = None
        self.front_html = ""
        self.back_html = ""
    
    @pyqtSlot()
    def onShowAnswerClicked(self):
        if self.back_html:
            self.show.emit(self.back_html)
    
    @pyqtSlot()
    def answerEasy(self): self._send_answer("Fácil")
    @pyqtSlot()
    def answerOk(self): self._send_answer("Ok")
    @pyqtSlot()
    def answerHard(self): self._send_answer("Difícil")
    @pyqtSlot()
    def answerFail(self): self._send_answer("Errei")
    
    @pyqtSlot()
    def toggleFullscreen(self):
        if self.app:
            self.app.toggle_fullscreen()
    
    @pyqtSlot()
    def snoozeCard(self):
        if self.app:
            self.app.snooze_current_card()
    
    def _send_answer(self, level: str):
        if self.pending_callback:
            cb = self.pending_callback
            self._reset()
            self.hide.emit()
            cb(level)
    
    def show_card(self, front_html: str, back_html: str, callback):
        self.pending_callback = callback
        self.front_html = front_html
        self.back_html = back_html
        self.show.emit(front_html)
    
    def _reset(self):
        self.pending_callback = None
        self.front_html = ""
        self.back_html = ""


# ───────────────── APP PRINCIPAL ─────────────────
class App:
    """Classe principal do Anki Booster"""
    
    def __init__(self):
        # Estado dos cards
        self.cards = []
        self.pool_cards = []
        self.active_cards = []

        # Estado persistente
        self.state = load_json_file(STATE_FILE, {})
        self.daily = load_json_file(DAILY_FILE, {"date": str(datetime.date.today()), "cards_today": {}})

        # Configuração
        self.config = load_config()
        self._apply_config_globals()

        # Controle de fluxo
        self.next_global_show = 0
        self.reviewing = False
        self.allow_showing = False
        self.paused = False
        self._current_card = None

        # Inicializa UI
        self.bridge = Bridge(self)
        self.engine = QQmlApplicationEngine()
        self.engine.rootContext().setContextProperty("bridge", self.bridge)
        qml_path = os.path.join(SCRIPT_DIR, "theme.qml")
        self.engine.load(QUrl.fromLocalFile(qml_path))
        
        if not self.engine.rootObjects():
            log("❌ Falha ao carregar theme.qml", "ERR")
            sys.exit(1)
        
        # Configura janela
        root = self.engine.rootObjects()[0]
        root.setMinimumWidth(440)
        root.setMaximumWidth(440)
        root.setMinimumHeight(320)
        root.setMaximumHeight(320)
        root.setSizeIncrement(QSize(0, 0))
        root.setFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        # Debug config
        log(f"🔍 CONFIG_FILE: {CONFIG_FILE}", "INFO")
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, encoding='utf-8') as f:
                    content = f.read()
                    log(f"📄 Config atual: {content[:300]}...", "INFO")
            except Exception as e:
                log(f"⚠️ Não foi possível ler config: {e}", "WARN")
        else:
            log(f"⚠️ Arquivo de config NÃO existe ainda", "WARN")

        # Inicia threads
        threading.Thread(target=self.tcp_listener, daemon=True).start()
        self.timer = QTimer()
        self.timer.timeout.connect(self.loop)
        self.timer.start(3000)
    
    def _apply_config_globals(self):
        """Aplica config para variáveis de acesso rápido"""
        global LIMIT_CARDS, GLOBAL_CORRECT, GLOBAL_WRONG, MAX_DAILY, BUFFER_SIZE
        global FAVS_PRIORITY, REVLOG_DAYS, REVLOG_TYPES, FAV_BONUS, FAV_LEVELS
        
        LIMIT_CARDS = self.config["LIMIT_CARDS"]
        GLOBAL_CORRECT = self.config["GLOBAL_CORRECT"]
        GLOBAL_WRONG = self.config["GLOBAL_WRONG"]
        MAX_DAILY = self.config["MAX_DAILY"]
        BUFFER_SIZE = self.config["BUFFER_SIZE"]
        FAVS_PRIORITY = self.config["FAVS_PRIORITY"]
        REVLOG_DAYS = self.config["REVLOG_DAYS"]
        REVLOG_TYPES = self.config.get("REVLOG_TYPES", [0, 1, 2, 3])
        FAV_BONUS = FAVS_PRIORITY
    
    # ───────────────── SNOOZE UTILS ─────────────────
    def snooze_current_card(self):
        """Adia o card atual por 1 hora (sem remover do buffer ou mudar streak ou qualquer coisa sobre o card)"""
        if not self._current_card:
            log("⚠️ Nenhum card ativo para snooze", "WARN")
            return
        
        cid = str(self._current_card["id"])
        now = time.time()
        snooze_delay = 3600
        
        self._current_card["next_due"] = now + snooze_delay
        self.state[cid] = self._current_card
        save_json_file(STATE_FILE, self.state)
        
        self.bridge.hide.emit()
        self.reviewing = False
        self._current_card = None
        #self.next_global_show = now + self.config["GLOBAL_CORRECT"]
        self.next_global_show = now # Força verificação imediata: snooze não deve atrasar o fluxo

        next_time = datetime.datetime.fromtimestamp(now + snooze_delay).strftime("%H:%M:%S")
        log(f"🌙 Card {cid} adiado por 1h (volta às {next_time})", "OK")
        #log("Ok, todos os snooze foram lidos")
    
    # ───────────────── TCP LISTENER ─────────────────
    def tcp_listener(self):
        """Listener TCP para comandos externos"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", CMD_PORT))
        sock.listen(5)
        log("-------------------------------------------------")
        log("📡 TCP pronto")

        while True:
            conn, _ = sock.accept()
            with conn:
                try:
                    cmd = conn.recv(4096).decode().strip()
                except Exception:
                    continue
                
                if not cmd:
                    continue
                log(f"⬇️ {cmd}")

                if cmd == "START":
                    today = str(datetime.date.today())
                    if self.daily.get("date") != today:
                        log(f"📅 Novo dia detectado ({today}), resetando contadores", "INFO")
                        self.daily = {"date": today, "cards_today": {}}
                        save_json_file(DAILY_FILE, self.daily)
                    
                    self.config = load_config()
                    self._apply_config_globals()
                    
                    # DEBUG: Log de carregamento de cards
                    log(f"🔍 Carregando cards do Anki (LIMIT_CARDS={LIMIT_CARDS}, FAVS_PRIORITY={FAVS_PRIORITY})...", "INFO")
                    self.cards = load_cards_from_anki(self.config, self.state, self.daily)
                    
                    if self.cards:
                        # DEBUG: Resumo dos cards carregados
                        favs_in_cards = [c for c in self.cards if str(c["id"]) in get_all_favs()]
                        log(f"✅ {len(self.cards)} cards carregados | {len(favs_in_cards)} são favoritos", "OK")
                        
                        # DEBUG: Lista favoritos que NÃO foram carregados (se houver)
                        all_favs = get_all_favs()
                        loaded_fav_ids = {str(c["id"]) for c in self.cards if str(c["id"]) in all_favs}
                        filtered_favs = [f for f in all_favs if f not in loaded_fav_ids]
                        
                        if filtered_favs:
                            reasons = []
                            now = time.time()
                            for cid in filtered_favs[:3]:  # Mostra os 3 primeiros pra não poluir
                                s_cid = self.state.get(cid, {})
                                due = s_cid.get("next_due", 0)
                                hits = self.daily.get("cards_today", {}).get(cid, 0)
                                
                                if due > now:
                                    wait_min = int((due - now) / 60)
                                    reasons.append(f"{cid} (snooze: {wait_min}min)")
                                elif hits >= 5:
                                    reasons.append(f"{cid} (limite diário: {hits}/5)")
                                else:
                                    reasons.append(f"{cid} (filtro)")
                            log(f"⏳ {len(filtered_favs)} favoritos agendados/filtrados: {', '.join(reasons)}{'...' if len(filtered_favs)>3 else ''}", "INFO")

                        
                        self.prepare_buffer()
                        self.allow_showing = True
                        conn.sendall(b"OK")
                        log("⬆️ OK", "OK")
                        log("-------------------------------------------------")
                    else:
                        if not is_anki_closed():
                            conn.sendall(b"ANKI_OPEN")
                        else:
                            conn.sendall(b"NO_CARDS")

                elif cmd == "GET_FAVS":
                    favs = get_all_favs()
                    conn.sendall(json.dumps(favs).encode())

                elif cmd.startswith("TOGGLE_FAV:"):
                    try:
                        cid = cmd.split(":", 1)[1]
                        toggle_fav(cid)
                        favs = get_all_favs()
                        conn.sendall(json.dumps(favs).encode())
                    except Exception as e:
                        log(f"❌ Erro ao toggle fav: {e}", "ERR")
                        conn.sendall(b"[]")

                elif cmd.startswith("SAVE_CONFIG:"):
                    try:
                        json_str = cmd[len("SAVE_CONFIG:"):]
                        new_cfg = json.loads(json_str)
                        
                        filtered_cfg = {k: v for k, v in new_cfg.items() if k in VALID_CONFIG_KEYS}
                        current_cfg = load_config()
                        final_cfg = {**current_cfg, **filtered_cfg}
                            
                        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                            json.dump(final_cfg, f, indent=2, ensure_ascii=False)
                        
                        log("------------------------------------------------", "INFO")
                        log("📋 Config salva:", "INFO")
                        for key in VALID_CONFIG_KEYS:
                            if key in filtered_cfg:
                                old_val = current_cfg.get(key)
                                new_val = final_cfg[key]
                                log(f"   {key}: {old_val} → {new_val} ✅", "OK")
                        
                        self.config = final_cfg
                        self._apply_config_globals()
                        
                        conn.sendall(b"OK")
                        log("⬆️ Config recebida e salva via TCP", "OK")
                        log("-------------------------------------------------", "INFO")
                            
                    except json.JSONDecodeError as e:
                        log(f"❌ JSON inválido: {e}", "ERR")
                        conn.sendall(b"INVALID_JSON")
                    except Exception as e:
                        log(f"❌ Erro ao salvar config: {e}", "ERR")
                        conn.sendall(b"SAVE_ERROR")

                elif cmd == "TOGGLE_PAUSE":
                    self.paused = not self.paused
                    estado = "PAUSED" if self.paused else "RUNNING"
                    log(f"⏸️ Booster {'PAUSADO' if self.paused else 'RETOMADO'}!", "WARN" if self.paused else "OK")
                    conn.sendall(estado.encode())

                elif cmd == "GET_CONFIG":
                    conn.sendall(json.dumps(self.config).encode())
                    log("⬆️ Config enviada via TCP (GET_CONFIG)", "INFO")

                else:
                    conn.sendall(b"UNKNOWN_CMD")
    
    # ───────────────── BUFFER UTILS ─────────────────
    def prepare_buffer(self):
        """Prepara buffer de cards ativos e pool de reserva"""
        self.pool_cards = self.cards.copy()
        self.active_cards = self.pool_cards[:BUFFER_SIZE]
        self.pool_cards = self.pool_cards[BUFFER_SIZE:]
        log(f"📦 Buffer {len(self.active_cards)} | Pool {len(self.pool_cards)}")
        
        # DEBUG: Mostra IDs no buffer ativo
        if self.active_cards:
            active_ids = [str(c["id"]) for c in self.active_cards]
            log(f"🔍 Buffer ativo: {active_ids[:3]}{'...' if len(active_ids)>3 else ''}", "INFO")

    # ───────────────── MAIN LOOP ─────────────────
    def loop(self):
        """Loop principal: verifica cards disponíveis e exibe"""
        if self.paused: return
        now = time.time()
        
        if now < self.next_global_show:
            return
        
        if not self.allow_showing or self.reviewing:
            return
            
        available_cards = [c for c in self.active_cards if c.get("next_due", 0) <= now]
        
        # Debug: Por que nenhum card disponível?
        if not available_cards and self.active_cards:
            blocked = [c for c in self.active_cards if c.get("next_due", 0) > now]
            log(f"⚠️ {len(blocked)}/{len(self.active_cards)} cards bloqueados por next_due", "WARN")
            if blocked:
                sample = blocked[0]
                log(f"🔍 Exemplo: CID {sample['id']} | next_due={sample['next_due']:.0f} | agora={now:.0f} | falta={(sample['next_due']-now)/60:.1f}min", "INFO")
            return
        if not available_cards:
            return
            
        favs_set = set(get_all_favs())
        
        # DEBUG: Calcula prioridade para cada card disponível (só log se tiver favoritos)
        favs_available = [c for c in available_cards if str(c["id"]) in favs_set]
        if favs_available:
            log(f"🔍 {len(favs_available)} favoritos disponíveis agora", "INFO")
            for c in favs_available[:2]:  # Só os 2 primeiros pra não spammar
                cid = str(c["id"])
                errors = c["errors_recent"]
                streak = c.get("streak", 0)
                fav_bonus = FAV_BONUS if cid in favs_set else 0
                priority = (-errors, streak, -fav_bonus)
                hits = self.daily["cards_today"].get(cid, 0)
                log(f"   📍 {cid} | errors={errors} | streak={streak} | fav_bonus={fav_bonus} | priority={priority} | hits={hits}/5", "INFO")
        
        card = min(
            available_cards,
            key=lambda c: (
                -c["errors_recent"],
                c.get("streak", 0),
                -(FAV_BONUS if str(c["id"]) in favs_set else 0)
            )
        )

        self.reviewing = True
        self.last_card_time = now
        self._current_card = card
        starred = str(card["id"]) in favs_set
        level = card.get("fav_level", 1) if starred else 1
        consecutive = card.get("fav_consecutive", 0) if starred else 0
        
        # DEBUG: Card selecionado
        log(f"🎯 Card selecionado: {card['id']} | fav={starred} | errors={card['errors_recent']} | streak={card.get('streak',0)}", "OK")
        
        front_wrapped = _wrap_html(card["front"], starred, level, consecutive, self.config)
        back_wrapped = _wrap_html(card["back"], starred, level, consecutive, self.config)
        self.bridge.show_card(front_wrapped, back_wrapped, lambda l: self.process_card(card, l))

    # ───────────────── CARD PROCESSOR ─────────────────
    def process_card(self, card: dict, level: str, favs_set: set = None):
        """Processa resposta do usuário e atualiza estado"""
        now = time.time()
        cid = str(card["id"])
        log(f"🧠 Processando {cid} com nível '{level}'")

        if favs_set is None:
            favs_set = set(get_all_favs())
        
        max_hits = 5 if cid in favs_set else MAX_DAILY
        count = self.daily["cards_today"].get(cid, 0)
        is_fav = cid in favs_set

        if level == "Fácil":
            count += 1
            card["streak"] += 2
            card["errors_recent"] = max(0, card["errors_recent"] - 2)
            card_delay = GLOBAL_CORRECT * 3 - 15
            log(f"✅ Fácil: streak +2, erros -2, delay = {card_delay/60:.1f}min", "OK")
            
        elif level == "Ok":
            count += 1
            card["streak"] += 2
            card["errors_recent"] = max(0, card["errors_recent"] - 1)
            card_delay = GLOBAL_CORRECT * 2 - 10
            log(f"👍 Ok: streak +2, erros -1, delay = {card_delay/60:.1f}min", "OK")
            
        elif level == "Difícil":
            count += 1
            card["streak"] += 1
            card_delay = GLOBAL_CORRECT * 1 - 18
            log(f"😢 Difícil: streak +1, delay = {card_delay/60:.1f}min", "INFO")
            
        elif level == "Errei":
            card["streak"] = 0
            card["errors_recent"] += 1
            card_delay = GLOBAL_WRONG
            log(f"💀 Errei: streak reset, erros +1, delay = {card_delay/60:.1f}min", "WARN")
        else:
            card_delay = GLOBAL_CORRECT
            log(f"⚠️ Nível desconhecido '{level}', usando delay padrão", "WARN")

        if is_fav and level != "Errei":
            card["fav_consecutive"] = card.get("fav_consecutive", 0) + 1
            current_level = card.get("fav_level", 1)
            required = FAV_LEVELS.get(current_level, 5)
            
            if card["fav_consecutive"] >= required:
                if current_level < 3:
                    card["fav_level"] = current_level + 1
                    card["fav_consecutive"] = 0
                    log(f"🆙 Favorito subiu para N{card['fav_level']}!", "OK")
                else:
                    graduate_fav(cid)
                    card["fav_level"] = 1
                    card["fav_consecutive"] = 0
                    log(f"🏆 Favorito N3 COMPLETO! Graduação realizada.", "OK")
            else:
                log(f"📈 Favorito N{current_level}: {card['fav_consecutive']}/{required}")
        elif is_fav and level == "Errei":
            old_level = card.get("fav_level", 1)
            card["fav_level"] = 1
            card["fav_consecutive"] = 0
            log(f"🔙 Favorito resetado do N{old_level} para N1", "WARN")

        card["next_due"] = float(now + card_delay)
        next_time = datetime.datetime.fromtimestamp(card["next_due"]).strftime("%H:%M:%S")
        log(f"⏳ Próxima exibição do card em {int(card_delay)}s ({next_time})")
        log("-------------------------------------------------")

        self.daily["cards_today"][cid] = count
        save_json_file(DAILY_FILE, self.daily)
        self.state[cid] = card
        save_json_file(STATE_FILE, self.state)
        self.last_card_correct = level != "Errei"

        try:
            idx = next(i for i, c in enumerate(self.active_cards) if c["id"] == card["id"])
            if count >= max_hits:
                log(f"🚫 Saiu ({count}/{max_hits})", "WARN")
                self.active_cards.pop(idx)
                if self.pool_cards:
                    self.active_cards.append(self.pool_cards.pop(0))
            else:
                log(f"🔄 Rotação ({count}/{max_hits})")
                log("-------------------------------------------------")
                self.active_cards.append(self.active_cards.pop(idx))
        except StopIteration:
            pass

        self.next_global_show = now + GLOBAL_CORRECT
        next_hr = datetime.datetime.fromtimestamp(self.next_global_show).strftime("%H:%M:%S")
        log(f"⏳ Ritmo global: próximo card em {GLOBAL_CORRECT}s ({next_hr})")
        self.reviewing = False
        self._current_card = None
    
    def toggle_fullscreen(self):
        """Alterna entre janela normal e fullscreen"""
        root = self.engine.rootObjects()[0] if self.engine.rootObjects() else None
        if not root:
            return
        
        if root.windowState() & Qt.WindowState.WindowFullScreen:
            root.setWindowState(Qt.WindowState.WindowNoState)
            root.setWidth(440)
            root.setHeight(320)
            log("🔲 Fullscreen DESATIVADO", "INFO")
        else:
            root.setWindowState(Qt.WindowState.WindowFullScreen)
            log("🔳 Fullscreen ATIVADO", "INFO")


# ───────────────── ENTRY POINT ─────────────────
if __name__ == "__main__":
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --no-sandbox --disable-software-rasterizer --allow-file-access-from-files --allow-file-access"
    
    app = QApplication(sys.argv)
    App()
    log(f"🚀 Booster rodando | FAVS_PRIORITY: {FAV_BONUS} | UI: QML")
    sys.exit(app.exec())