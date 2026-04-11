import socket, json
from . import config
from . import furigana_hover
from aqt import gui_hooks, mw
from aqt.reviewer import Reviewer

BOOSTER_HOST = "127.0.0.1"
BOOSTER_PORT = 8894

# -----------------------------
# Função para enviar comando ao Booster
# -----------------------------
def send_command(cmd):
    try:
        with socket.create_connection((BOOSTER_HOST, BOOSTER_PORT), timeout=1) as s:
            s.sendall(cmd.encode())
            data = s.recv(65536).decode()
            return data
    except Exception as e:
        print(f"[Booster][ERR] Erro ao enviar comando: {e}")
        return None

# -----------------------------
# Função JS para injetar/atualizar estrela
# -----------------------------
def inject_star_button(card, reviewer: Reviewer, favorites):
    card_id = str(card.id)
    star_char = "⭐" if card_id in favorites else "☆"

    js = f"""
    (function() {{
        function addButton() {{
            let btn = document.getElementById('booster_star');
            if(!btn) {{
                btn = document.createElement('button');
                btn.id = 'booster_star';
                btn.style.position = 'absolute';
                btn.style.top = '10px';
                btn.style.right = '10px';
                btn.style.fontSize = '24px';
                btn.style.zIndex = '9999';
                btn.style.cursor = 'pointer';
                btn.onclick = function() {{ pycmd("toggle_fav:{card_id}"); }};
                document.body.appendChild(btn);
            }}
            btn.innerText = '{star_char}';
        }}
        if(document.readyState === "complete") {{
            addButton();
        }} else {{
            window.addEventListener('load', addButton);
            setTimeout(addButton, 100);  // fallback rápido
        }}
    }})();
    """
    reviewer.web.eval(js)

# -----------------------------
# Evento: card exibido → atualiza estrela
# -----------------------------
def on_card_shown(card):
    reviewer = mw.reviewer
    # consulta favs via TCP
    data = send_command(f"GET_FAVS")
    favorites = []
    if data:
        try:
            favorites = json.loads(data)
        except:
            pass

    # transforma todos em string, garante comparação correta
    favorites = [str(cid) for cid in favorites]

    # injeta botão com estrela correta
    inject_star_button(card, reviewer, favorites)

gui_hooks.reviewer_did_show_question.append(on_card_shown)

# -----------------------------
# Evento: clique na estrela → alterna favorito
# -----------------------------
def pycmd_bridge(handled, message, context):
    if message.startswith("toggle_fav:"):
        card_id = int(message.split(":")[1])
        result = send_command(f"TOGGLE_FAV:{card_id}")
        added = False
        if result:
            try:
                fav_list = json.loads(result)
                added = str(card_id) in fav_list
            except:
                pass

        # Atualiza estrela imediatamente
        reviewer = mw.reviewer
        js = f"""
        (function() {{
            let btn = document.getElementById('booster_star');
            if(btn) btn.innerText = {"'⭐'" if added else "'☆'"};
        }})();
        """
        reviewer.web.eval(js)

        return True, None  # <-- CORREÇÃO AQUI

    return False, None

gui_hooks.webview_did_receive_js_message.append(pycmd_bridge)

# -----------------------------
# Evento opcional: fechar perfil → sincroniza Booster
# -----------------------------
def on_profile_closed():
    send_command("START")

gui_hooks.profile_will_close.append(on_profile_closed)
