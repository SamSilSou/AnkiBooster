#!/usr/bin/env python3
from aqt import mw, gui_hooks
from aqt.qt import *
import json, os, socket
from pathlib import Path

# 📂 Caminho LOCAL da extensão
CONFIG_PATH = Path(__file__).parent / "booster_config.json"
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

# 🔧 Configurações padrão
DEFAULT_CONFIG = {
    "GLOBAL_CORRECT": 1200,
    "GLOBAL_WRONG": 300,
    "BUFFER_SIZE": 5,
    "MAX_DAILY": 3,
    "REVLOG_DAYS": 3,
    "LIMIT_CARDS": 200,
    "FAVS_PRIORITY": 3,
    "REVLOG_TYPES": [0,1,2,3]  # 🔥 NOVO
}

CMD_PORT = 8894

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception as e:
            print(f"⚠️ Erro ao carregar config: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar config: {e}")
        return False

def check_booster_connection():
    try:
        with socket.create_connection(("127.0.0.1", CMD_PORT), timeout=1):
            return True
    except:
        return False

def send_config_to_booster(cfg):
    try:
        with socket.create_connection(("127.0.0.1", CMD_PORT), timeout=2) as s:
            payload = json.dumps(cfg, separators=(',', ':'))
            s.sendall(f"SAVE_CONFIG:{payload}".encode())
            response = s.recv(1024).decode()
            return response == "OK"
    except Exception as e:
        print(f"[Booster] ⚠️ Falha ao enviar config: {e}")
        return False

def send_toggle_pause_to_booster():
    try:
        with socket.create_connection(("127.0.0.1", CMD_PORT), timeout=2) as s:
            s.sendall(b"TOGGLE_PAUSE")
            return s.recv(1024).decode()
    except:
        return None


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
    cfg = load_config()
    d = QDialog(mw)
    d.setWindowTitle("⚙️ Booster Config 🔥")
    d.setMinimumWidth(450)

    layout = QVBoxLayout()
    sliders = {}

    # Status
    status_box = QHBoxLayout()
    status_label = QLabel("Verificando...")
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

    # 🔥 REVLOG TYPES
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

    # Botões

    # 🔌 Botão Pausar/Retomar
    btn_pause = QPushButton("⏸️ Pausar Booster")
    btn_pause.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; padding: 8px;")

    def toggle_pause():
        if not check_booster_connection():
            feedback_label.setText("❌ Booster offline")
            return
        state = send_toggle_pause_to_booster()
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

    btn_row = QHBoxLayout()
    btn_save = QPushButton("💾 Salvar")
    btn_reset = QPushButton("♻️ Resetar")

    def save():
        new_cfg = {k: sliders[k].value() for k in sliders}

        selected_types = [t for t, cb in type_checkboxes.items() if cb.isChecked()]
        if not selected_types:
            selected_types = [0,1,2,3]

        new_cfg["REVLOG_TYPES"] = selected_types

        if not save_config(new_cfg):
            feedback_label.setText("❌ Erro ao salvar")
            return

        if send_config_to_booster(new_cfg):
            feedback_label.setText("✅ Sincronizado")
        else:
            feedback_label.setText("⚠️ Booster offline")

        QTimer.singleShot(1500, d.accept)

    def reset():
        for k in sliders:
            sliders[k].setValue(DEFAULT_CONFIG[k])

        for t, cb in type_checkboxes.items():
            cb.setChecked(t in DEFAULT_CONFIG["REVLOG_TYPES"])

        feedback_label.setText("♻️ Resetado (salve para aplicar)")

    btn_save.clicked.connect(save)
    btn_reset.clicked.connect(reset)

    btn_row.addWidget(btn_reset)
    btn_row.addWidget(btn_save)
    layout.addLayout(btn_row)

    d.setLayout(layout)
    d.exec()

def on_profile_will_close():
    cfg = load_config()
    if check_booster_connection():
        send_config_to_booster(cfg)

def init_menu():
    action = QAction("Booster Config ⚙️", mw)
    action.triggered.connect(open_config)
    mw.form.menuTools.addAction(action)

gui_hooks.profile_will_close.append(on_profile_will_close)
init_menu()