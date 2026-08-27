#!/usr/bin/env python3
"""
Anki Booster - Serviço Principal (CÉREBRO ÚNICO)
Lógica de UI, TCP, loop e processamento de cards.
Service como fonte única da verdade; utils apenas executa.
Tentei documentar as principais mudanças que realizei, porém não falo muito inglês kkk
Logo, para obter uma documentação mais precisa, utilizei minha língua-mãe (Português do Brasil).
Desde já agradeço a todo e qualquer auxílio, pois o fiz no meu tempo livre e, portanto, tenho certeza de que existem erros e bugs não percebidos.
Utilizo no meu dia a dia esse sistema maravilhoso e sinto uma enorme diferença entre uma revisão e outra no Anki.
À medida que uso, corrijo os bugs; portanto, como usuário e desenvolvedor, agradeço toda e qualquer ajuda.
MUITO OBRIGADO por usar e por colaborar 😁❣️

--------------------------------------------------------------------------
CHANGELOG DESTA REVISÃO (correções aplicadas):
1. FAVS_PRIORITY agora participa do SCORE de prioridade (não é mais um
   desempate de última hora que praticamente nunca era consultado).
2. O log de debug de favoritos no loop() passou a usar a MESMA função
   _calculate_priority() usada na escolha real do card, evitando que o
   log mostre uma fórmula diferente da que decide de fato.
3. Corrigido NameError em TOGGLE_PAUSE (usava 'paused' em vez de
   'self.paused' dentro da f-string).
4. prepare_buffer() agora adquire _state_lock, pois é chamado tanto pela
   thread principal (tray) quanto pela thread do TCP listener.
5. Parsing de favoritos (fav_ints) não descarta mais TODOS os favoritos
   quando um único cid é inválido - ignora só o item problemático.
6. generate_anki_report() (em booster_utils.py) teve o cabeçalho
   realinhado com as colunas realmente escritas no corpo.
7. NOVO: refresh periódico da fila de cards (self.cards / active_cards /
   pool_cards). Antes, a lista de cards era montada UMA VEZ no START e
   nunca mais atualizada até o próximo START manual - então um card
   errado no Anki "de verdade" (fora do Oboete) durante o dia nunca
   entrava na rotação, e a lógica de "priorizar dificuldade recente"
   ficava cada vez mais desatualizada quanto mais tempo o serviço
   ficasse rodando em background. Agora existe um QTimer separado
   (REFRESH_INTERVAL_MIN, configurável via addon) que reconsulta o Anki
   e refaz a fila periodicamente, preservando streak/errors_recent/
   next_due (que vêm do self.state, não da query) e sem interromper um
   card que esteja em exibição no momento do refresh.
8. NOVO (usabilidade, requer theme.qml atualizado):
   - Bridge.toggleFavorite() + currentIsFavorite: favoritar/desfavoritar
     o card ATUAL direto do popup, sem precisar sair do Booster.
   - Bridge.answered(str): feedback textual curto (streak / tempo até
     reaparecer) exibido no popup por ~0.9s antes de esconder, em vez de
     esconder imediatamente sem informação nenhuma sobre a consequência
     da resposta.
   - show_card() agora recebe card_id/starred, necessários pro botão de
     favoritar saber em qual card agir.
--------------------------------------------------------------------------
"""

import sys, os, time, socket, datetime, json, threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty, QUrl, QTimer, QSize, Qt
from PyQt6.QtGui import QIcon
from booster_tray import BoosterTray
from booster_logger import BoosterLogger
from booster_utils import set_logger

from booster_utils import (
    SCRIPT_DIR, BOOSTER_DATA_DIR, STATE_FILE, DAILY_FILE, CONFIG_FILE, CMD_PORT,
    load_config, load_json_file, save_json_file,
    log, get_all_favs, toggle_fav, graduate_fav, is_anki_closed, get_anki_db,
    _wrap_html, load_cards_from_anki,
    load_theme, set_theme, generate_anki_report
)

VALID_CONFIG_KEYS = {
    "GLOBAL_CORRECT", "GLOBAL_WRONG", "BUFFER_SIZE", "MAX_DAILY", "REVLOG_DAYS",
    "LIMIT_CARDS", "FAVS_PRIORITY", "REVLOG_TYPES", "FRONT_FIELDS", "BACK_FIELDS",
    "MIN_CARD_DELAY", "HIDE_FURIGANA_ON_HOVER", "FAV_MAX_DAILY", "FAV_LEVEL_THRESHOLDS",
    "REFRESH_INTERVAL_MIN"
}

FAV_LEVELS = {1: 6, 2: 4, 3: 2}
_state_lock = threading.Lock()

# Escala que converte o slider FAVS_PRIORITY (1-10 na UI, 0-N no backend)
# em pontos dentro do mesmo espaço de disputa do score de dificuldade.
# Referência: 1 lapse recente do Anki vale 100 pontos, 1 erro do Booster
# vale 50, 1 lapse histórico vale 5. Um FAVS_PRIORITY=3 (default) então
# vale 60 pontos - comparável a pouco mais de meio "erro recente do Anki".
FAV_PRIORITY_SCALE = 20

LIMIT_CARDS = GLOBAL_CORRECT = GLOBAL_WRONG = MAX_DAILY = BUFFER_SIZE = FAV_MAX_DAILY = None
FAVS_PRIORITY = REVLOG_DAYS = REVLOG_TYPES = FAV_BONUS = None
REFRESH_INTERVAL_MIN = None

# Força Qt a usar o tema do sistema (GTK3 no Linux, Windows10/11 no Win)
if sys.platform == "linux":
    os.environ.setdefault("QT_QPA_PLATFORMTHEME", "gtk3")
elif sys.platform == "win32":
    os.environ.setdefault("QT_QPA_PLATFORMTHEME", "windows10")

os.environ.setdefault("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1")

class Bridge(QObject):
    show = pyqtSignal(str)
    hide = pyqtSignal()
    themeChanged = pyqtSignal()
    # NOVO: feedback textual pós-resposta (streak/tempo até reaparecer),
    # emitido antes do hide para o QML poder exibir por um instante.
    answered = pyqtSignal(str)
    # NOVO: notifica o QML quando o status de favorito do card atual muda,
    # seja por show_card() (novo card) ou por toggleFavorite() (usuário
    # favoritou/desfavoritou pelo próprio popup).
    favoriteChanged = pyqtSignal()

    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.pending_callback = None
        self.front_html = ""
        self.back_html = ""
        # NOVO: id e status de favorito do card atualmente exibido, usados
        # pelo botão de favoritar direto no popup (toggleFavorite()).
        self.current_card_id = None
        self._is_favorite = False

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

    @pyqtSlot(int)
    def snoozeWithMinutes(self, minutes: int):
        minutes = max(1, min(120, minutes))
        if self.app:
            self.app.snooze_current_card(minutes)

    @pyqtProperty("QVariant", notify=themeChanged)
    def theme(self):
        """Expõe o tema atual para o QML"""
        return load_theme()

    @pyqtSlot(str)
    def setTheme(self, theme_name: str):
        """Troca o tema e salva no themes.json"""
        if set_theme(theme_name):
            self.themeChanged.emit()

    @pyqtProperty(bool, notify=favoriteChanged)
    def currentIsFavorite(self):
        """Expõe pro QML se o card atualmente exibido é favorito."""
        return self._is_favorite

    @pyqtSlot()
    def toggleFavorite(self):
        """
        Favorita/desfavorita o card ATUAL diretamente pelo popup, sem
        precisar sair do Booster. Antes só era possível via TCP/Anki.
        """
        if self.current_card_id is None:
            return
        if self.app:
            self.app.toggle_current_favorite(str(self.current_card_id))
        self._is_favorite = not self._is_favorite
        self.favoriteChanged.emit()

    def _send_answer(self, level: str):
        if self.pending_callback:
            cb = self.pending_callback
            self._reset()
            # NOVO: process_card() agora retorna um texto curto (streak +
            # tempo até reaparecer). Mostramos esse texto no popup por um
            # instante ANTES de esconder a janela, em vez de esconder
            # imediatamente sem nenhum feedback informativo sobre o que
            # a resposta acabou de causar no sistema.
            feedback_text = None
            try:
                feedback_text = cb(level)
            except Exception as e:
                if self.app and getattr(self.app, "logger", None):
                    self.app.logger.log(f"⚠️ Erro ao processar resposta: {e}", "WARN")
            if feedback_text:
                self.answered.emit(feedback_text)
                QTimer.singleShot(900, self.hide.emit)
            else:
                self.hide.emit()

    def show_card(self, front_html: str, back_html: str, callback, card_id=None, starred: bool = False):
        self.pending_callback = callback
        self.front_html = front_html
        self.back_html = back_html
        # NOVO: guarda id/status de favorito do card atual, usado pelo
        # botão de favoritar do popup (toggleFavorite()/currentIsFavorite).
        self.current_card_id = card_id
        self._is_favorite = starred
        self.favoriteChanged.emit()
        self.show.emit(front_html)

    def _reset(self):
        self.pending_callback = None
        self.front_html = ""
        self.back_html = ""
        # current_card_id/_is_favorite NÃO são limpos aqui de propósito:
        # o popup pode continuar mostrando o card por um instante (durante
        # o feedback pós-resposta) e o botão de favoritar deve continuar
        # funcional/coerente até a janela realmente esconder.


class App:
    def __init__(self):
        self.cards, self.pool_cards, self.active_cards = [], [], []
        self.state = load_json_file(STATE_FILE, {})
        self.daily = load_json_file(DAILY_FILE, {"date": str(datetime.date.today()), "cards_today": {}})

        self.config = load_config()
        self._apply_config_globals()

        self.next_global_show = 0
        self.reviewing = False
        self.allow_showing = False
        self.paused = False
        self._current_card = None

        self.logger = BoosterLogger(
            buffer_max=200,
            port=8895,
            script_dir=SCRIPT_DIR
        )
        self.logger.start_server(daemon=True)
        set_logger(self.logger)

        self.bridge = Bridge(self)

        self.engine = QQmlApplicationEngine()
        self.engine.rootContext().setContextProperty("bridge", self.bridge)
        qml_path = os.path.join(SCRIPT_DIR, "theme.qml")
        self.engine.load(QUrl.fromLocalFile(qml_path))

        if not self.engine.rootObjects():
            self.logger.log("❌ Falha ao carregar theme.qml", "ERR")
            sys.exit(1)

        root = self.engine.rootObjects()[0]
        root.setMinimumWidth(440)
        root.setMaximumWidth(440)
        root.setMinimumHeight(320)
        root.setMaximumHeight(320)
        root.setSizeIncrement(QSize(0, 0))
        root.setFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.BypassWindowManagerHint
        )

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, encoding='utf-8') as f:
                    content = f.read()
                    self.logger.log(f"📄 Config atual: {content[:200]}...", "INFO")
            except Exception as e:
                self.logger.log(f"⚠️ Não foi possível ler config: {e}", "WARN")

        threading.Thread(target=self.tcp_listener, daemon=True).start()
        self.timer = QTimer()
        self.timer.timeout.connect(self.loop)
        self.timer.start(3000)

        # Timer de refresh periódico da fila de cards (ver changelog no
        # topo do arquivo, item 7). Criado desligado por padrão até o
        # primeiro _apply_config_globals() já ter rodado (ele já rodou,
        # no __init__, então isso liga o timer com o valor real do config).
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_cards)
        self._reschedule_refresh_timer()

        self.tray = BoosterTray()
        self.tray.start_requested.connect(self._tray_start)
        self.tray.pause_requested.connect(lambda: self._set_paused(True))
        self.tray.resume_requested.connect(lambda: self._set_paused(False))
        self.tray.toggle_window_requested.connect(self._toggle_window_visibility)
        self.tray.quit_requested.connect(QApplication.quit)

    def _apply_config_globals(self):
        global LIMIT_CARDS, GLOBAL_CORRECT, GLOBAL_WRONG, MAX_DAILY, BUFFER_SIZE, FAV_MAX_DAILY
        global FAVS_PRIORITY, REVLOG_DAYS, REVLOG_TYPES, FAV_BONUS, REFRESH_INTERVAL_MIN

        try:
            # Default alinhado com o que o addon de config assume (ver anki_booster_config.py)
            LIMIT_CARDS = max(1, int(self.config.get("LIMIT_CARDS", 200)))
            GLOBAL_CORRECT = max(60, int(self.config.get("GLOBAL_CORRECT", 1200)))
            GLOBAL_WRONG = max(30, int(self.config.get("GLOBAL_WRONG", 300)))
            MAX_DAILY = max(1, int(self.config.get("MAX_DAILY", 3)))
            BUFFER_SIZE = max(1, int(self.config.get("BUFFER_SIZE", 5)))
            FAV_MAX_DAILY = max(1, int(self.config.get("FAV_MAX_DAILY", 5)))
            FAVS_PRIORITY = max(0, int(self.config.get("FAVS_PRIORITY", 3)))
            REVLOG_DAYS = max(0, int(self.config.get("REVLOG_DAYS", 3)))
            # 0 = refresh periódico desligado (comportamento antigo: só
            # atualiza a fila em START manual). Mínimo de 5min quando
            # ligado, pra não ficar martelando o SQLite do Anki.
            raw_refresh = max(0, int(self.config.get("REFRESH_INTERVAL_MIN", 20)))
            REFRESH_INTERVAL_MIN = 0 if raw_refresh == 0 else max(5, raw_refresh)
        except (ValueError, TypeError):
            self.logger.log("⚠️ Config com valor inválido, usando fallback", "WARN")
            LIMIT_CARDS, GLOBAL_CORRECT, GLOBAL_WRONG = 200, 1200, 300
            MAX_DAILY, BUFFER_SIZE, FAV_MAX_DAILY = 3, 5, 5
            FAVS_PRIORITY, REVLOG_DAYS = 3, 3
            REFRESH_INTERVAL_MIN = 20

        REVLOG_TYPES = self.config.get("REVLOG_TYPES", [0, 1, 2, 3])
        FAV_BONUS = FAVS_PRIORITY

        # Reaplica o intervalo no timer de refresh, se ele já existir
        # (chamado de novo depois de SAVE_CONFIG via TCP).
        if hasattr(self, "refresh_timer"):
            self._reschedule_refresh_timer()

    def _toggle_window_visibility(self):
        root = self.engine.rootObjects()[0] if self.engine.rootObjects() else None
        if root:
            if root.isVisible():
                root.hide()
            else:
                root.show()
                root.raise_()
                root.requestActivate()

    def _set_paused(self, paused: bool):
        self.paused = paused
        self.tray.set_paused(paused)
        self.logger.log(f"⏸️ Booster {'PAUSADO' if paused else 'RETOMADO'} via Tray", "OK" if not paused else "WARN")

    def _load_favs_safely(self) -> tuple[list, list]:
        """
        Converte a lista de favoritos (strings) em ints para a query SQL,
        ignorando individualmente qualquer cid malformado, em vez de
        descartar TODOS os favoritos se um único item for inválido.
        """
        favs = get_all_favs()
        fav_ints = []
        for f in favs:
            try:
                fav_ints.append(int(f))
            except (ValueError, TypeError):
                self.logger.log(f"⚠️ Favorito com cid inválido ignorado: {f!r}", "WARN")
        return favs, fav_ints

    def _load_and_start(self, conn=None):
        """
        Fluxo único de início de sessão, usado tanto pelo tray quanto pelo
        comando TCP START. Antes essa lógica estava duplicada em dois
        lugares (_tray_start e _handle_tcp_cmd), o que é o motivo mais
        provável de bugs como o do TOGGLE_PAUSE só terem sido corrigidos
        em um dos dois lugares.
        """
        today = str(datetime.date.today())

        if self.daily.get("date") != today:
            favs = set(get_all_favs())
            self.daily = {
                "date": today,
                "cards_today": {cid: hits for cid, hits in self.daily.get("cards_today", {}).items() if cid in favs}
            }
            save_json_file(DAILY_FILE, self.daily)
            self.logger.log("📅 Dia virado: daily.json atualizado", "INFO")

        self.config = load_config()
        self._apply_config_globals()
        self.logger.log(f"🔍 Carregando cards (LIMIT_CARDS={LIMIT_CARDS}, FAVS_PRIORITY={FAVS_PRIORITY})...", "INFO")

        anki_db = get_anki_db()
        if not anki_db:
            if conn:
                conn.sendall(b"NO_CARDS")
            else:
                self.logger.log("❌ Não foi possível localizar o banco do Anki", "ERR")
            return

        with _state_lock:
            self.cards = load_cards_from_anki(
                anki_db_path=anki_db,
                favs=get_all_favs(),
                state=self.state,
                daily=self.daily,
                revlog_days=REVLOG_DAYS,
                revlog_types=REVLOG_TYPES,
                limit_cards=LIMIT_CARDS,
                front_fields=self.config.get("FRONT_FIELDS"),
                back_fields=self.config.get("BACK_FIELDS"),
            )

        favs_temp = set(get_all_favs())
        self.cards.sort(key=lambda c: self._calculate_priority(c, favs_temp))

        report_path = os.path.join(BOOSTER_DATA_DIR, "anki_booster_stats.txt")
        generate_anki_report(self.cards, report_path)

        if self.cards:
            favs_in_cards = [c for c in self.cards if str(c["id"]) in favs_temp]
            self.logger.log(f"✅ {len(self.cards)} cards carregados | {len(favs_in_cards)} são favoritos", "OK")

            loaded_fav_ids = {str(c["id"]) for c in self.cards if str(c["id"]) in favs_temp}
            filtered_favs = [f for f in favs_temp if f not in loaded_fav_ids]

            if filtered_favs:
                reasons = []
                now = time.time()
                for cid in list(filtered_favs)[:3]:
                    s_cid = self.state.get(cid, {})
                    due = s_cid.get("next_due", 0)
                    hits = self.daily.get("cards_today", {}).get(cid, 0)
                    if due > now:
                        wait_min = int((due - now) / 60)
                        reasons.append(f"{cid} (snooze: {wait_min}min)")
                    elif hits >= FAV_MAX_DAILY:
                        reasons.append(f"{cid} (limite diário: {hits}/{FAV_MAX_DAILY})")
                    else:
                        reasons.append(f"{cid} (filtro)")
                self.logger.log(f"⏳ {len(filtered_favs)} favoritos agendados/filtrados: {', '.join(reasons)}", "INFO")

            self.prepare_buffer()
            self.allow_showing = True
            QTimer.singleShot(0, lambda: self.tray.set_running(True))
            if conn:
                conn.sendall(b"OK")
                self.logger.log("⬆️ OK", "OK")
            self.logger.log("-------------------------------------------------")
        else:
            self.logger.log("⚠️ Nenhum card disponível para iniciar", "WARN")
            if conn:
                if not is_anki_closed():
                    conn.sendall(b"ANKI_OPEN")
                else:
                    conn.sendall(b"NO_CARDS")

    def _tray_start(self):
        """Inicia o Booster via tray (chamado por sinal do BoosterTray)"""
        self._load_and_start(conn=None)

    def _reschedule_refresh_timer(self):
        """
        (Re)agenda o QTimer de refresh periódico usando REFRESH_INTERVAL_MIN
        atual. Chamado no __init__ e sempre que a config é recarregada
        (_apply_config_globals), então mudar o slider no addon e salvar já
        aplica o novo intervalo sem precisar reiniciar o serviço.
        """
        self.refresh_timer.stop()
        if REFRESH_INTERVAL_MIN and REFRESH_INTERVAL_MIN > 0:
            interval_ms = REFRESH_INTERVAL_MIN * 60 * 1000
            self.refresh_timer.start(interval_ms)
            self.logger.log(f"🔄 Refresh periódico da fila: a cada {REFRESH_INTERVAL_MIN}min", "INFO")
        else:
            self.logger.log("🔄 Refresh periódico da fila: DESLIGADO (REFRESH_INTERVAL_MIN=0)", "INFO")

    def _refresh_cards(self):
        """
        Reconsulta o Anki e refaz self.cards / active_cards / pool_cards,
        sem interromper uma sessão que ainda não foi iniciada nem um card
        que esteja em exibição no momento do refresh.

        Isso resolve o problema de a fila ficar "congelada" no estado do
        último START manual: sem isso, um card errado no Anki de verdade
        (fora do Oboete) ou um favorito que passou a ter revlog recente
        nunca entraria na rotação até o usuário reiniciar manualmente.

        streak/errors_recent/next_due não se perdem nesse processo, pois
        load_cards_from_anki() sempre os repopula a partir de self.state,
        que não é tocado aqui - só a LISTA de quais cards existem é
        reconstruída.
        """
        if not self.allow_showing:
            # Sessão ainda não foi iniciada (nenhum START ainda) - nada a
            # refrescar, evita disparar START implícito sem o usuário pedir.
            return
        if self.reviewing:
            # Um card está na tela agora; adia para o próximo ciclo do
            # timer em vez de trocar active_cards/pool_cards embaixo dele.
            self.logger.log("🔄 Refresh adiado: card em exibição no momento", "INFO")
            return

        self.logger.log("-------------------------------------------------")
        self.logger.log("🔄 Refresh periódico: revalidando fila com o Anki", "INFO")
        self._load_and_start(conn=None)

    def toggle_current_favorite(self, cid: str):
        """
        Favorita/desfavorita um card via SQLite (booster_utils), chamado
        pelo Bridge.toggleFavorite() quando o usuário clica na estrela do
        popup. toggle_fav já é importado no topo do arquivo.
        """
        toggle_fav(cid)
        self.logger.log(f"⭐ Favorito alternado via popup para o card {cid}", "OK")

    def snooze_current_card(self, minutes: int = 60):
        if not self._current_card:
            self.logger.log("⚠️ Nenhum card ativo para snooze", "WARN")
            return
        cid = str(self._current_card["id"])
        now = time.time()
        snooze_delay = minutes * 60
        self._current_card["next_due"] = now + snooze_delay
        self.state[cid] = self._current_card
        save_json_file(STATE_FILE, self.state)
        self.bridge.hide.emit()
        self.reviewing = False
        self._current_card = None
        self.next_global_show = now
        next_time = datetime.datetime.fromtimestamp(now + snooze_delay).strftime("%H:%M")
        self.logger.log(f"🌙 Card {cid} adiado por {minutes}min (volta às {next_time})", "OK")

    def _handle_tcp_cmd(self, conn, cmd: str):
        if cmd == "START":
            self._load_and_start(conn=conn)

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
                self.logger.log(f"❌ Erro ao toggle fav: {e}", "ERR")
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
                self.logger.log("------------------------------------------------", "INFO")
                self.logger.log("📋 Config salva:", "INFO")
                for key in VALID_CONFIG_KEYS:
                    if key in filtered_cfg:
                        old_val = current_cfg.get(key)
                        new_val = final_cfg[key]
                        self.logger.log(f"   {key}: {old_val} → {new_val} ✅", "OK")
                self.config = final_cfg
                self._apply_config_globals()
                conn.sendall(b"OK")
                self.logger.log("⬆️ Config recebida e salva via TCP", "OK")
                self.logger.log("-------------------------------------------------", "INFO")
            except json.JSONDecodeError as e:
                self.logger.log(f"❌ JSON inválido: {e}", "ERR")
                conn.sendall(b"INVALID_JSON")
            except Exception as e:
                self.logger.log(f"❌ Erro ao salvar config: {e}", "ERR")
                conn.sendall(b"SAVE_ERROR")
        elif cmd == "TOGGLE_PAUSE":
            # FIX: usava 'paused' (não definido neste escopo) em vez de
            # 'self.paused' -> causava NameError sempre que este comando
            # era recebido via TCP.
            self.paused = not self.paused
            QTimer.singleShot(0, lambda: self.tray.set_paused(self.paused))
            estado = "PAUSED" if self.paused else "RUNNING"
            self.logger.log(
                f"⏸️ Booster {'PAUSADO' if self.paused else 'RETOMADO'}!",
                "WARN" if self.paused else "OK"
            )
            conn.sendall(estado.encode())
        elif cmd == "GET_CONFIG":
            conn.sendall(json.dumps(self.config).encode())
            self.logger.log("⬆️ Config enviada via TCP", "INFO")
        else:
            conn.sendall(b"UNKNOWN_CMD")

    def tcp_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", CMD_PORT))
        sock.listen(5)
        self.logger.log("-------------------------------------------------")
        self.logger.log("📡 TCP pronto")

        while True:
            try:
                conn, _ = sock.accept()
                conn.settimeout(30)
                with conn:
                    try:
                        cmd = conn.recv(4096).decode().strip()
                    except (socket.timeout, Exception):
                        continue
                    if not cmd:
                        continue
                    self.logger.log(f"⬇️ {cmd}")
                    try:
                        self._handle_tcp_cmd(conn, cmd)
                    except Exception as e:
                        # Isola o listener de qualquer bug futuro em _handle_tcp_cmd
                        # (é o mesmo tipo de exceção que o NameError do TOGGLE_PAUSE
                        # provocava antes do fix).
                        self.logger.log(f"❌ Erro ao processar comando '{cmd}': {e}", "ERR")
                        try:
                            conn.sendall(b"INTERNAL_ERROR")
                        except OSError:
                            pass
            except OSError:
                break

    def prepare_buffer(self):
        # FIX: agora protegido por _state_lock, pois é chamado tanto pela
        # thread principal (tray) quanto pela thread do TCP listener, e
        # reatribui active_cards/pool_cards que também são lidos/escritos
        # em loop() e process_card() sob o mesmo lock.
        with _state_lock:
            safe_buffer = max(1, BUFFER_SIZE or 1)
            self.pool_cards = self.cards.copy()
            self.active_cards = self.pool_cards[:safe_buffer]
            self.pool_cards = self.pool_cards[safe_buffer:]
        self.logger.log(f"📦 Buffer {len(self.active_cards)} | Pool {len(self.pool_cards)}")

    def _calculate_priority(self, card: dict, favs_set: set) -> tuple:
        """
        Calcula a prioridade de exibição de um card.

        Filosofia:
        O Booster deve priorizar dificuldades RECENTES em vez de
        dificuldades históricas. Se um card foi errado hoje, ele deve
        aparecer antes de um card que acumulou lapses há meses, mas que
        atualmente está sendo respondido corretamente.

        Score principal:
            +100 -> Cada "Again" recente registrado no revlog do Anki
            +50  -> Cada erro recente registrado pelo próprio Booster
            +5   -> Cada lapse histórico acumulado pelo Anki
            +FAVS_PRIORITY * FAV_PRIORITY_SCALE -> Card é favorito

        FIX (era o motivo de FAVS_PRIORITY não funcionar):
        Antes, o "bônus" de favorito só era usado como 5º critério de
        desempate (depois de score, ease, interval e streak). Como esses
        campos são praticamente contínuos, na prática dois cards quase
        nunca empatavam nos 4 primeiros - então o slider de "prioridade
        de favoritos" na UI não tinha efeito observável nenhum.
        Agora o bônus entra DENTRO do score, na mesma escala de pontos
        que os outros fatores de dificuldade, então FAVS_PRIORITY de fato
        empurra favoritos pra frente da fila de forma proporcional ao
        valor configurado (0 = sem bônus, 10 = bônus de 200 pontos,
        equivalente a 2 lapses recentes do Anki).

        Desempates (ordem de prioridade):
            1. Score total de dificuldade (já inclui o bônus de favorito)
            2. Ease do Anki (menor = mais difícil)
            3. Intervalo do Anki (menor = menos consolidado)
            4. Streak do Booster (menor = menos dominado)

        Observação:
        A função retorna uma tupla lexicográfica utilizada por min().
        Quanto MENOR a tupla, MAIOR a prioridade do card.
        """

        cid_str = str(card["id"])

        anki_lapses = card.get("anki_lapses", 0)
        anki_ease = card.get("anki_ease", 250)
        anki_interval = card.get("anki_interval", 0)
        anki_revlog_lapses = card.get("anki_revlog_lapses", 0)

        booster_errors = card.get("errors_recent", 0)
        booster_streak = card.get("streak", 0)

        is_fav = cid_str in favs_set
        fav_bonus_points = (FAVS_PRIORITY * FAV_PRIORITY_SCALE) if is_fav else 0

        score = (
            anki_revlog_lapses * 100 +
            booster_errors * 50 +
            anki_lapses * 5 +
            fav_bonus_points
        )

        return (
            -score,           # 1º: dificuldade recente (já pondera favoritos)
            anki_ease,        # 2º: ease menor = mais difícil
            anki_interval,    # 3º: intervalo menor = menos consolidado
            booster_streak,   # 4º: streak menor = menos dominado
        )

    def loop(self):
        if self.paused: return
        now = time.time()
        if now < self.next_global_show:
            return
        if not self.allow_showing or self.reviewing:
            return

        with _state_lock:
            active_cards_copy = self.active_cards.copy()
            daily_copy = {"cards_today": dict(self.daily.get("cards_today", {}))}

        favs_set = set(get_all_favs())

        available_cards = [
            c for c in active_cards_copy
            if c.get("next_due", 0) <= now
            and daily_copy["cards_today"].get(str(c["id"]), 0) < (FAV_MAX_DAILY if str(c["id"]) in favs_set else MAX_DAILY)
        ]

        if not available_cards and active_cards_copy:
            blocked = [c for c in active_cards_copy if c.get("next_due", 0) > now]
            self.logger.log(f"⚠️ {len(blocked)}/{len(active_cards_copy)} cards bloqueados por next_due", "WARN")
            if blocked:
                sample = blocked[0]
                self.logger.log(f"🔍 Exemplo: CID {sample['id']} | next_due={sample['next_due']:.0f} | agora={now:.0f} | falta={(sample['next_due']-now)/60:.1f}min", "INFO")
            return
        if not available_cards:
            return

        favs_available = [c for c in available_cards if str(c["id"]) in favs_set]
        if favs_available:
            self.logger.log(f"🔍 {len(favs_available)} favoritos disponíveis agora", "INFO")
            for c in favs_available[:2]:
                cid = str(c["id"])
                # FIX: antes esse log recalculava uma fórmula de prioridade
                # DIFERENTE da usada de verdade no min() abaixo
                # ((-errors, streak, -fav_bonus), sem ease/interval/score real).
                # Agora usa a mesma _calculate_priority() que decide o card,
                # então o log deixa de "mentir" sobre o motivo da escolha.
                priority = self._calculate_priority(c, favs_set)
                hits = daily_copy["cards_today"].get(cid, 0)
                self.logger.log(f"   📍 {cid} | priority={priority} | hits={hits}/{FAV_MAX_DAILY}", "INFO")

        card = min(available_cards, key=lambda c: self._calculate_priority(c, favs_set))

        self.reviewing = True
        self.last_card_time = now
        self._current_card = card
        starred = str(card["id"]) in favs_set
        level = card.get("fav_level", 1) if starred else 1
        consecutive = card.get("fav_consecutive", 0) if starred else 0
        self.logger.log("-------------------------------------------------")
        self.logger.log(f"🎯 Card selecionado: {card['id']} | fav={starred} | errors={card.get('errors_recent', 0)} | streak={card.get('streak',0)}", "OK")

        front_wrapped = _wrap_html(
            card["front"],
            starred=starred,
            level=level,
            consecutive=consecutive,
            fav_thresholds=FAV_LEVELS,
            hide_furigana=self.config.get("HIDE_FURIGANA_ON_HOVER", False)
        )
        back_wrapped = _wrap_html(
            card["back"],
            starred=starred,
            level=level,
            consecutive=consecutive,
            fav_thresholds=FAV_LEVELS,
            hide_furigana=self.config.get("HIDE_FURIGANA_ON_HOVER", False)
        )
        self.bridge.show_card(
            front_wrapped, back_wrapped,
            lambda l: self.process_card(card, l, favs_set),
            card_id=card["id"], starred=starred
        )

    def process_card(self, card: dict, level: str, favs_set: set = None):
        now = time.time()
        cid = str(card["id"])
        self.logger.log(f"🧠 Processando {cid} com nível '{level}'")

        if favs_set is None:
            favs_set = set(get_all_favs())

        max_hits = FAV_MAX_DAILY if cid in favs_set else MAX_DAILY
        count = self.daily["cards_today"].get(cid, 0)
        is_fav = cid in favs_set

        if level == "Fácil":
            count += 1
            card["streak"] += 1
            card["errors_recent"] = max(0, card["errors_recent"] - 2)
            card_delay = GLOBAL_CORRECT * 5 - 15
            self.logger.log(f"✅ Fácil: streak +1, erros -2, delay = {card_delay/60:.1f}min", "OK")
        elif level == "Ok":
            count += 1
            card["streak"] += 1
            card["errors_recent"] = max(0, card["errors_recent"] - 1)
            card_delay = GLOBAL_CORRECT * 2.5 - 10
            self.logger.log(f"👍 Ok: streak +1, erros -1, delay = {card_delay/60:.1f}min", "OK")
        elif level == "Difícil":
            count += 1
            card["streak"] += 1
            card_delay = GLOBAL_CORRECT * 1 - 18
            self.logger.log(f"😢 Difícil: streak +1, delay = {card_delay/60:.1f}min", "INFO")
        elif level == "Errei":
            card["streak"] = 0
            card["errors_recent"] += 1
            card_delay = GLOBAL_WRONG
            self.logger.log(f"💀 Errei: streak reset, erros +1, delay = {card_delay/60:.1f}min", "WARN")
        else:
            card_delay = GLOBAL_CORRECT
            self.logger.log(f"⚠️ Nível desconhecido '{level}', usando delay padrão", "WARN")

        if is_fav and level != "Errei":
            card["fav_consecutive"] = card.get("fav_consecutive", 0) + 1
            current_level = card.get("fav_level", 1)
            required = FAV_LEVELS.get(current_level, 5)
            if card["fav_consecutive"] >= required:
                if current_level < 3:
                    card["fav_level"] = current_level + 1
                    card["fav_consecutive"] = 0
                    self.logger.log(f"🆙 Favorito subiu para N{card['fav_level']}!", "OK")
                else:
                    graduate_fav(cid)
                    card["fav_level"] = 1
                    card["fav_consecutive"] = 0
                    self.logger.log("🏆 Favorito N3 COMPLETO! Graduação realizada.", "OK")
            else:
                self.logger.log(f"📈 Favorito N{current_level}: {card['fav_consecutive']}/{required}")
        elif is_fav and level == "Errei":
            old_level = card.get("fav_level", 1)
            card["fav_level"] = 1
            card["fav_consecutive"] = 0
            self.logger.log(f"🔙 Favorito resetado do N{old_level} para N1", "WARN")

        card["next_due"] = float(now + card_delay)
        next_time = datetime.datetime.fromtimestamp(card["next_due"]).strftime("%H:%M:%S")
        self.logger.log(f"⏳ Próxima exibição do card em {int(card_delay)}s ({next_time})")

        self.daily["cards_today"][cid] = count
        save_json_file(DAILY_FILE, self.daily)
        self.state[cid] = card
        save_json_file(STATE_FILE, self.state)
        self.last_card_correct = level != "Errei"

        with _state_lock:
            idx = next((i for i, c in enumerate(self.active_cards) if c["id"] == card["id"]), None)
            if idx is not None:
                if count >= max_hits:
                    self.logger.log(f"🚫 Limite diário atingido ({count}/{max_hits})", "WARN")
                    self.logger.log("-------------------------------------------------")
                    self.active_cards.pop(idx)
                    if self.pool_cards:
                        self.active_cards.append(self.pool_cards.pop(0))
                else:
                    self.logger.log(f"🔄 Rotação | Card tem {count}/{max_hits} acertos hoje", "OK")
                    self.logger.log("-------------------------------------------------")
                    self.active_cards.append(self.active_cards.pop(idx))

        self.next_global_show = min(now + GLOBAL_CORRECT, now + card_delay)
        delay_real = int(self.next_global_show - now)
        next_hr = datetime.datetime.fromtimestamp(self.next_global_show).strftime("%H:%M:%S")
        source = "card_delay" if card_delay < GLOBAL_CORRECT else "GLOBAL_CORRECT"
        self.logger.log(f"⏳ Ritmo global: próximo card em {delay_real}s ({next_hr}) [fonte: {source}]")
        self.logger.log("-------------------------------------------------")

        self.reviewing = False
        self._current_card = None

        # NOVO: texto curto de feedback informativo, exibido no popup por
        # ~0.9s antes de esconder (ver Bridge._send_answer). Antes disso,
        # a única forma de saber "streak" ou "quando volta" era abrir o
        # log técnico - agora aparece no próprio popup.
        delay_min = max(0, int(card_delay / 60))
        icons = {"Fácil": "✅", "Ok": "👍", "Difícil": "😢", "Errei": "💀"}
        icon = icons.get(level, "ℹ️")
        if level == "Errei":
            feedback_text = f"{icon} Volta em {delay_min}min"
        else:
            feedback_text = f"{icon} Streak {card['streak']} · volta em {delay_min}min"
        return feedback_text

    def toggle_fullscreen(self):
        root = self.engine.rootObjects()[0] if self.engine.rootObjects() else None
        if not root:
            return
        if root.windowState() & Qt.WindowState.WindowFullScreen:
            root.setWindowState(Qt.WindowState.WindowNoState)
            root.setWidth(440)
            root.setHeight(320)
            self.logger.log("🔲 Fullscreen DESATIVADO", "INFO")
        else:
            root.setWindowState(Qt.WindowState.WindowFullScreen)
            self.logger.log("🔳 Fullscreen ATIVADO", "INFO")


if __name__ == "__main__":
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--disable-gpu --no-sandbox --disable-software-rasterizer "
        "--allow-file-access-from-files --allow-file-access "
        "--enable-features=WebUIDarkMode,OverlayScrollbar"
    )
    app = QApplication(sys.argv)
    app_instance = App()

    log(f"🚀 Booster rodando | FAVS_PRIORITY: {FAV_BONUS} | UI: QML")

    sys.exit(app.exec())
