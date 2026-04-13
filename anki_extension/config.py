#!/usr/bin/env python3
"""
Anki Booster Addon - Config UI via TCP
Sem arquivo local. Lê/salva direto no serviço principal.
"""
from aqt import mw, gui_hooks
from aqt.qt import *
import json, socket

CMD_PORT = 8894
BOOSTER_ADDR = ("127.0.0.1", CMD_PORT)

# 🔧 Defaults apenas para UI/fallback (não são salvos em disco)
DEFAULTS = {
    "GLOBAL_CORRECT": 1200,
    "GLOBAL_WRONG": 300,
    "BUFFER_SIZE": 5,
    "MAX_DAILY": 3,
    "REVLOG_DAYS": 3,
    "LIMIT_CARDS": 200,
    "FAVS_PRIORITY": 3,
    "REVLOG_TYPES": [0,1,2,3],
    "HIDE_FURIGANA_ON_HOVER": False
}

# ───────────────── TCP HELPERS ─────────────────
def tcp_request(cmd: str) -> str | None:
    """Envia comando TCP e retorna resposta completa"""
    try:
        with socket.create_connection(BOOSTER_ADDR, timeout=2) as s:
            s.sendall(cmd.encode())
            data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk: break
                data += chunk
                if len(chunk) < 4096: break
            return data.decode()
    except:
        return None

def fetch_config():
    """Busca config atual do Booster via TCP"""
    res = tcp_request("GET_CONFIG")
    if res:
        try: return {**DEFAULTS, **json.loads(res)}
        except: pass
    return None

def push_config(cfg: dict) -> bool:
    """Envia config completa para o Booster"""
    payload = json.dumps(cfg, separators=(',', ':'))
    return tcp_request(f"SAVE_CONFIG:{payload}") == "OK"

def toggle_pause_cmd() -> str | None:
    """Envia comando de pause/resume"""
    return tcp_request("TOGGLE_PAUSE")

def check_booster_connection() -> bool:
    """Verifica apenas se a porta está aberta"""
    try:
        with socket.create_connection(BOOSTER_ADDR, timeout=1): return True
    except: return False

# ───────────────── UI COMPONENTS ─────────────────
def make_slider(title, emoji, min_v, max_v, step, value, desc):
    box = QVBoxLayout()
    label = QLabel(f"{emoji} <b>{title}</b>")
    box.addWidget(label)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setMinimum(min_v)
    slider.setMaximum(max_v)
    slider.setSingleStep(step)
    slider.setValue(value)

    value_label = QLabel(str(value))
    value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
    value_label.setStyleSheet("font-weight: bold; color: #4A90D9;")

    slider.valueChanged.connect(lambda v: value_label.setText(str(v)))

    desc_label = QLabel(f"<i>{desc}</i>")
    desc_label.setStyleSheet("color: gray; font-size: 11px;")

    row = QHBoxLayout()
    row.addWidget(slider)
    row.addWidget(value_label)

    box.addLayout(row)
    box.addWidget(desc_label)
    return box, slider

def open_config():
    # Busca config diretamente do Booster, caso não encontre retorna booster desconectado
    cfg = fetch_config()
    if cfg is None:
        QMessageBox.warning(mw, "Booster Offline", 
            "⚠️ Não foi possível conectar ao serviço.\n"
            "Inicie o Anki Booster antes de abrir as configurações.")
        return

    d = QDialog(mw)
    d.setWindowTitle("⚙️ Booster Config 🔥")
    d.setMinimumWidth(450)

    layout = QVBoxLayout()
    sliders = {}

    # Status
    status_box = QHBoxLayout()
    status_label = QLabel("🟢 Booster conectado")
    status_label.setStyleSheet("color: green; font-weight: bold;")
    btn_refresh = QPushButton("🔄")
    btn_refresh.setFixedWidth(40)

    def update_status():
        if check_booster_connection():
            status_label.setText("🟢 Booster conectado")
            status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            status_label.setText("🔴 Booster não encontrado")
            status_label.setStyleSheet("color: red; font-weight: bold;")

    btn_refresh.clicked.connect(update_status)
    status_box.addWidget(status_label)
    status_box.addWidget(btn_refresh)
    layout.addLayout(status_box)
    update_status()

    layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

    # CHECKBOX FURIGANA HOVER, um sistema que esconde o Ruby pra forçar memorização
    furigana_cb = QCheckBox("🈶 Ocultar furigana (RUBY) até passar o mouse")
    furigana_cb.setChecked(cfg.get("HIDE_FURIGANA_ON_HOVER", False))
    furigana_cb.setStyleSheet("font-size: 13px; padding: 4px 0;")
    layout.addWidget(furigana_cb)

    layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

    # Sliders
    sliders_list = [
        ("FAVS_PRIORITY", "Prioridade dos favoritos", "⭐", 1, 10, 1, "Quanto maior, mais favoritos aparecem"),
        ("GLOBAL_CORRECT", "Tempo após acerto", "✅", 60, 3600, 30, "Tempo até reaparecer após acerto"),
        ("GLOBAL_WRONG", "Tempo após erro", "❌", 30, 600, 10, "Tempo após erro"),
        ("BUFFER_SIZE", "Buffer", "📦", 1, 20, 1, "Cards simultâneos"),
        ("MAX_DAILY", "Máx por dia", "🔁", 1, 10, 1, "Repetições por dia"),
        ("REVLOG_DAYS", "Dias do histórico", "📅", 1, 30, 1, "Busca no revlog"),
        ("LIMIT_CARDS", "Limite de cards", "🎴", 50, 500, 50, "Máximo carregado"),
    ]

    for key, title, emoji, min_v, max_v, step, desc in sliders_list:
        box, s = make_slider(title, emoji, min_v, max_v, step, cfg[key], desc)
        sliders[key] = s
        layout.addLayout(box)

    # REVLOG TYPES: tipos de estado de aprendizado para serem considerados no revlog
    types_box = QVBoxLayout()
    types_box.addWidget(QLabel("🧠 <b>Tipos de revisão</b>"))

    type_options = [
        (0, "Learning"),
        (1, "Review"),
        (2, "Relearning"),
        (3, "Cram"),
    ]

    type_checkboxes = {}
    row = QHBoxLayout()

    for t, name in type_options:
        cb = QCheckBox(name)
        cb.setChecked(t in cfg.get("REVLOG_TYPES", [0,1,2,3]))
        type_checkboxes[t] = cb
        row.addWidget(cb)

    types_box.addLayout(row)

    desc = QLabel("<i>Quais tipos do revlog considerar</i>")
    desc.setStyleSheet("color: gray; font-size: 11px;")
    types_box.addWidget(desc)

    layout.addLayout(types_box)

    feedback_label = QLabel("")
    layout.addWidget(feedback_label)

    # Botão Pausar/Retomar
    btn_pause = QPushButton("⏸️ Pausar Booster")
    btn_pause.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; padding: 8px;")

    def toggle_pause():
        if not check_booster_connection():
            feedback_label.setText("❌ Booster offline")
            return
        state = toggle_pause_cmd()
        if state == "PAUSED":
            btn_pause.setText("▶️ Retomar Booster")
            btn_pause.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 8px;")
            feedback_label.setText("⏸️ Booster pausado! Nenhum card será exibido.")
        elif state == "RUNNING":
            btn_pause.setText("⏸️ Pausar Booster")
            btn_pause.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; padding: 8px;")
            feedback_label.setText("▶️ Booster retomado!")
        else:
            feedback_label.setText("⚠️ Falha na comunicação")
        QTimer.singleShot(2000, lambda: feedback_label.setText(""))

    btn_pause.clicked.connect(toggle_pause)
    layout.addWidget(btn_pause)
    layout.addWidget(QFrame(frameShape=QFrame.Shape.HLine))

    # Botões Salvar/Reset
    btn_row = QHBoxLayout()
    btn_save = QPushButton("💾 Salvar")
    btn_reset = QPushButton("♻️ Resetar")

    def save():
        new_cfg = {k: sliders[k].value() for k in sliders}
        selected_types = [t for t, cb in type_checkboxes.items() if cb.isChecked()]
        new_cfg["REVLOG_TYPES"] = selected_types if selected_types else [0,1,2,3]
        new_cfg["HIDE_FURIGANA_ON_HOVER"] = furigana_cb.isChecked()

        if push_config(new_cfg):
            feedback_label.setText("✅ Sincronizado com o Booster")
            QTimer.singleShot(1000, d.accept)
        else:
            feedback_label.setText("❌ Falha ao salvar. Verifique se o Booster está rodando.")

    def reset():
        for k in sliders:
            sliders[k].setValue(DEFAULTS[k])
        for t, cb in type_checkboxes.items():
            cb.setChecked(t in DEFAULTS["REVLOG_TYPES"])
        furigana_cb.setChecked(DEFAULTS["HIDE_FURIGANA_ON_HOVER"])
        feedback_label.setText("♻️ Resetado (salve para aplicar)")

    btn_save.clicked.connect(save)
    btn_reset.clicked.connect(reset)

    btn_row.addWidget(btn_reset)
    btn_row.addWidget(btn_save)
    layout.addLayout(btn_row)

    d.setLayout(layout)
    d.exec()

# ───────────────── INIT ─────────────────
def init_menu():
    action = QAction("🚀 Booster Config ⚙️", mw)
    action.triggered.connect(open_config)
    mw.form.menuTools.addAction(action)

# Removido: gui_hooks.profile_will_close.append(...)
# Motivo: Não há mais arquivo local para sincronizar no fechamento, então achei que era codigo inutil, se eu voltar atrás o coloce de volta
init_menu()