#!/usr/bin/env python3
"""
🔧 Anki Booster - Utilitários
Funções de path, config, log, DB, HTML e mídia.
"""
import os, sys, json, sqlite3, datetime, platform, pathlib, re, base64, shutil, tempfile, time
from typing import Optional, List, Dict, Any

# ───────────────── PATHS CROSS-PLATFORM ─────────────────
def get_script_dir() -> str:
    """Retorna o diretório onde o script está localizado"""
    return os.path.dirname(os.path.abspath(__file__))

def get_anki_base_path() -> str:
    """Retorna o caminho base do Anki conforme o SO"""
    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
        return os.path.join(appdata, "Anki2")
    else:
        flatpak = os.path.expanduser("~/.var/app/net.ankiweb.Anki/data/Anki2")
        if os.path.isdir(flatpak):
            return flatpak
        return os.path.expanduser("~/.local/share/Anki2")

# Diretório do script + pasta anki_booster
SCRIPT_DIR = get_script_dir()
BOOSTER_DATA_DIR = os.path.join(SCRIPT_DIR, "anki_booster")
os.makedirs(BOOSTER_DATA_DIR, exist_ok=True)

# Arquivos de estado
STATE_FILE = os.path.join(BOOSTER_DATA_DIR, "anki_booster_state.json")
DAILY_FILE = os.path.join(BOOSTER_DATA_DIR, "anki_booster_daily.json")
DB_FILE = os.path.join(BOOSTER_DATA_DIR, "anki_booster.db")
CONFIG_FILE = os.path.join(BOOSTER_DATA_DIR, "anki_booster_config.json")
CMD_PORT = 8894

# Caminho base do Anki
BASE_ANKI = get_anki_base_path()

# ───────────────── CONFIG PADRÃO ─────────────────
DEFAULT_CONFIG = {
    "GLOBAL_CORRECT": 1200,
    "GLOBAL_WRONG": 300,
    "BUFFER_SIZE": 5,
    "MAX_DAILY": 3,
    "REVLOG_DAYS": 3,
    "LIMIT_CARDS": 200,
    "FAVS_PRIORITY": 3,
    "REVLOG_TYPES": [0, 1, 2, 3],
    "FRONT_FIELDS": None,
    "BACK_FIELDS": None,
    "MIN_CARD_DELAY": 20,
    "HIDE_FURIGANA_ON_HOVER": False  # 🈶 Oculta furigana até hover no popup
}

def load_config() -> Dict[str, Any]:
    """Carrega config do arquivo ou retorna padrão, com logs de erro"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding='utf-8') as f:
                loaded = json.load(f)
                log(f"📄 Config carregada: {CONFIG_FILE}", "INFO")
                return {**DEFAULT_CONFIG, **loaded}
        except json.JSONDecodeError as e:
            log(f"❌ JSON inválido em {CONFIG_FILE}: {e}", "ERR")
        except PermissionError:
            log(f"❌ Sem permissão para ler {CONFIG_FILE}", "ERR")
        except Exception as e:
            log(f"❌ Erro ao carregar config: {type(e).__name__}: {e}", "ERR")
    else:
        log(f"📄 Config não encontrada, usando padrão", "INFO")
    return DEFAULT_CONFIG.copy()

# ───────────────── LOG UTILS ─────────────────
def log(msg: str, level: str = "INFO") -> None:
    """Log colorido com emoji e timestamp"""
    colors = {"INFO": "\033[94m", "OK": "\033[92m", "ERR": "\033[91m", "WARN": "\033[93m"}
    emojis = {"INFO": "📘", "OK": "✅", "ERR": "❌", "WARN": "⚠️"}
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"{colors[level]}{emojis[level]} [{now}] {msg}\033[0m", flush=True)

# ───────────────── JSON UTILS ─────────────────
def load_json_file(path: str, default: Any) -> Any:
    """Carrega JSON com fallback"""
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return default

def save_json_file(path: str, data: Any) -> None:
    """Salva JSON com criação de diretório"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ───────────────── FAVORITOS (SQLite local) ─────────────────
_fav_conn: Optional[sqlite3.Connection] = None

def _get_fav_conn() -> sqlite3.Connection:
    """Lazy init da conexão com o DB de favoritos"""
    global _fav_conn
    if _fav_conn is None:
        _fav_conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        _fav_conn.execute("CREATE TABLE IF NOT EXISTS favs (cid TEXT PRIMARY KEY)")
        _fav_conn.commit()
    return _fav_conn

def get_all_favs() -> List[str]:
    """Retorna lista de CIDs favoritos"""
    conn = _get_fav_conn()
    return [r[0] for r in conn.execute("SELECT cid FROM favs")]

def toggle_fav(cid: str) -> List[str]:
    """Adiciona ou remove favorito com rollback em caso de erro"""
    try:
        cid = str(cid).strip()
        conn = _get_fav_conn()
        current_favs = get_all_favs()
        
        if cid in current_favs:
            conn.execute("DELETE FROM favs WHERE cid=?", (cid,))
            log(f"⭐ Removido favorito {cid}", "OK")
        else:
            conn.execute("INSERT OR IGNORE INTO favs VALUES (?)", (cid,))
            log(f"⭐ Adicionado favorito {cid}", "OK")
            
        conn.commit()
        return get_all_favs()
    except Exception as e:
        log(f"❌ Erro ao salvar favorito {cid}: {e}", "ERR")
        if _fav_conn:
            _fav_conn.rollback()
        return []

def graduate_fav(cid: str) -> None:
    """Remove favorito após graduação completa"""
    conn = _get_fav_conn()
    conn.execute("DELETE FROM favs WHERE cid=?", (cid,))
    conn.commit()
    log(f"🎓 Favorito {cid} GRADUADO!", "OK")

# ───────────────── CHECK ANKI ─────────────────
def get_anki_db() -> Optional[str]:
    """Retorna o caminho do collection.anki2 do perfil ativo"""
    if not os.path.exists(BASE_ANKI):
        log(f"❌ BASE_ANKI não existe: {BASE_ANKI}", "ERR")
        return None

    for p in os.listdir(BASE_ANKI):
        profile_path = os.path.join(BASE_ANKI, p)
        db_path = os.path.join(profile_path, "collection.anki2")
        if os.path.isdir(profile_path) and os.path.exists(db_path):
            return db_path

    log("❌ Nenhum collection.anki2 encontrado!", "ERR")
    return None

def is_anki_closed() -> bool:
    """Verifica se o banco do Anki está liberado (não em uso)"""
    try:
        anki_db = get_anki_db()
        if not anki_db:
            return False
        db_uri = pathlib.Path(anki_db).as_uri()
        conn = sqlite3.connect(f"{db_uri}?mode=ro", uri=True)
        conn.execute("SELECT 1")
        conn.close()
        return True
    except sqlite3.OperationalError:
        return False
    except Exception:
        return False

# ───────────────── HTML WRAPPER ─────────────────
def _wrap_html(content: str, starred: bool = False, level: int = 1, consecutive: int = 0, config: dict = None) -> str:
    """Envolve o conteúdo do card com CSS e indicadores de favorito"""
    star_html = "⭐" if starred else ""
    level_html = f" <span style='font-size:12px;color:#ffd700'>[N{level}: {consecutive}/{_get_fav_level_max(level)}]</span>" if starred else ""
    
    hide_scrollbar_css = """
    <style>
        html, body {
            margin: 0; padding: 0; height: 100%;
            overflow-y: auto !important; overflow-x: hidden !important;
            scrollbar-width: none !important; -ms-overflow-style: none !important;
        }
        ::-webkit-scrollbar { display: none !important; width: 0 !important; background: transparent !important; }
        ::-webkit-scrollbar-thumb { display: none !important; background: transparent !important; }
        ::-webkit-scrollbar-track { display: none !important; }
    </style>
    """

    # 🈶 CSS Furigana Hover (injetado no popup se ativado)
    furigana_css = ""
    if config and config.get("HIDE_FURIGANA_ON_HOVER"):
        furigana_css = """
        <style>
        @media (hover: hover) {
            ruby rt {
                opacity: 0;
                transition: opacity 0.2s ease;
                pointer-events: none;
            }
            ruby:hover rt {
                opacity: 1;
            }
        }
        @media (hover: none) {
            ruby rt { opacity: 1 !important; }
        }
        </style>
        """
    
    return f"""
    {hide_scrollbar_css}
    {furigana_css}
    <div style="text-align:center;line-height:1.5;padding:10px;min-height:100vh;display:flex;align-items:center;justify-content:center;box-sizing:border-box;">
        <div style="position:absolute;top:8px;right:12px;font-size:20px;filter:drop-shadow(0 0 4px gold);">
            {star_html}{level_html}
        </div>
        <div style="display:inline-block;text-align:center;max-width:100%;">
            {content}
        </div>
    </div>
    """

def _get_fav_level_max(level: int) -> int:
    """Retorna o número de acertos necessários para o nível de favorito"""
    return {1: 5, 2: 3, 3: 2}.get(level, 5)

# ───────────────── MEDIA PARSER (Áudio Base64) ─────────────────
def _parse_anki_media(text: str, media_dir: Optional[str]) -> str:
    """
    Converte tags [sound:xxx.mp3] do Anki para <audio> HTML5 embutido em Base64.
    """
    if not text or not media_dir:
        return text

    def replace_audio(match):
        filename = match.group(1).strip().replace('\\', '/')
        filepath = os.path.join(media_dir, filename)
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                
                ext = os.path.splitext(filename)[1].lower()
                mime_map = {
                    '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg',
                    '.wav': 'audio/wav', '.flac': 'audio/flac'
                }
                mime = mime_map.get(ext, 'audio/mpeg')
                
                return f'<audio controls src="data:{mime};base64,{b64}"></audio>'
            except Exception as e:
                log(f"⚠️ Erro ao ler áudio {filename}: {e}", "WARN")
                return f'<span style="color:red; font-size:12px">[Audio: {filename}]</span>'
        
        return match.group(0)

    return re.sub(r'\[sound:([^\]]+)\]', replace_audio, text, flags=re.IGNORECASE)

# ───────────────── CARD LOADER ─────────────────
def load_cards_from_anki(
    config: Dict[str, Any],
    state: Dict[str, Any],
    daily: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Carrega cards do banco do Anki com filtros e processamento.
    """
    log("📂 Lendo Anki (revlog + favoritos)...")
    temp_dir = None
    
    try:
        temp_dir = tempfile.mkdtemp(prefix="anki_booster_")
        temp_db = os.path.join(temp_dir, "collection.anki2")
        ANKI_DB = get_anki_db()
        
        if not ANKI_DB:
            return []
            
        shutil.copy2(ANKI_DB, temp_db)

        cutoff = int((time.time() - config["REVLOG_DAYS"] * 24 * 60 * 60) * 1000)
        favs = get_all_favs()
        conn = sqlite3.connect(temp_db)

        # Query: Favoritos
        fav_raw = []
        fav_ints = []
        
        if favs:
            try:
                fav_ints = [int(f) for f in favs]
            except ValueError:
                fav_ints = []

            if fav_ints:
                fav_placeholders = ','.join('?' * len(fav_ints))
                fav_raw = conn.execute(f"""
                    SELECT DISTINCT c.id, n.flds, n.mid 
                    FROM cards c 
                    JOIN notes n ON c.nid = n.id 
                    WHERE c.id IN ({fav_placeholders})
                """, fav_ints).fetchall()

        # Query: Não-favoritos
        revlog_types = config["REVLOG_TYPES"] if isinstance(config["REVLOG_TYPES"], list) else [0,1,2,3]
        revlog_placeholders = ','.join(map(str, revlog_types))
        
        exclude_clause = f"AND c.id NOT IN ({','.join(['?']*len(fav_ints))})" if fav_ints else ""
        non_fav_query = f"""
            SELECT DISTINCT c.id, n.flds, n.mid 
            FROM cards c 
            JOIN notes n ON c.nid = n.id 
            JOIN revlog r ON c.id = r.cid 
            WHERE r.id > ? AND r.type IN ({revlog_placeholders}) {exclude_clause}
        """
        
        non_fav_params = (cutoff,) + tuple(fav_ints) if fav_ints else (cutoff,)
        non_fav_raw = conn.execute(non_fav_query, non_fav_params).fetchall()

        # Extrai modelos do Anki
        models_map = {}
        try:
            col_data = conn.execute("SELECT models FROM col").fetchone()
            if col_data and col_data[0]:
                models = json.loads(col_data[0])
                for mid_str, model in models.items():
                    mid_val = int(mid_str)
                    fld_names = [f['name'] for f in model.get('flds', [])]
                    qfmt = model.get('tmpls', [{}])[0].get('qfmt', '')
                    used = set(re.findall(r'\{[\{#^]?\s*(?:[\w]+:)?\s*([^\s{}]+?)\s*[\}]?\}', qfmt))
                    f_idx = [i for i, n in enumerate(fld_names) if n in used] or [0]
                    b_idx = [i for i in range(len(fld_names)) if i not in f_idx] or list(range(len(fld_names)))
                    models_map[mid_val] = (f_idx, b_idx)
        except Exception as e:
            log(f"⚠️ Falha ao ler modelos do Anki: {e}", "WARN")

        conn.close()
        
        # Combina e filtra únicos
        raw = fav_raw + non_fav_raw
        seen = set()
        unique_raw = [(cid, flds, mid) for cid, flds, mid in raw if cid not in seen and not seen.add(cid)]

        # Monta lista final
        MEDIA_DIR = os.path.join(os.path.dirname(ANKI_DB), "collection.media")
        cards = []
        
        for cid, flds, mid_val in unique_raw:
            all_f = flds.split("\x1f")
            s = state.get(str(cid), {})

            front_cfg = config.get("FRONT_FIELDS")
            back_cfg = config.get("BACK_FIELDS")
            
            if front_cfg is not None:
                front_idxs = list(range(len(all_f))) if front_cfg == [] else front_cfg
                back_idxs = list(range(len(all_f))) if (back_cfg is None or back_cfg == []) else back_cfg
            else:
                front_idxs, back_idxs = models_map.get(mid_val, ([0], list(range(len(all_f)))))

            front_parts = [all_f[i] for i in front_idxs if 0 <= i < len(all_f) and all_f[i].strip()]
            back_parts = [all_f[i] for i in back_idxs if 0 <= i < len(all_f) and all_f[i].strip()]

            front_html = "<br>".join(_parse_anki_media(f, MEDIA_DIR) for f in front_parts)
            back_html = "<br>".join(_parse_anki_media(f, MEDIA_DIR) for f in back_parts)

            cards.append({
                "id": cid,
                "front": front_html,
                "back": back_html,
                "streak": s.get("streak", 0),
                "errors_recent": s.get("errors_recent", 0),
                "fav_level": s.get("fav_level", 1) if str(cid) in favs else 1,
                "fav_consecutive": s.get("fav_consecutive", 0) if str(cid) in favs else 0,
                "next_due": float(s.get("next_due", 0))  # Garante tipo numérico
            })

        # Filtra por limite diário e agendamento
        valid_cards = []
        for c in cards:
            cid_str = str(c["id"])
            hits = daily.get("cards_today", {}).get(cid_str, 0)
            is_fav = cid_str in favs
            limit = 5 if is_fav else config["MAX_DAILY"]
            next_due = c.get("next_due", 0)
            now = time.time()
            
            if next_due <= now and hits < limit:
                valid_cards.append(c)

        # Ordenação final
        fav_bonus = config["FAVS_PRIORITY"]
        valid_cards.sort(key=lambda c: (
            -c["errors_recent"],
            c.get("streak", 0),
            -(fav_bonus if str(c["id"]) in favs else 0)
        ))

        return valid_cards[:config["LIMIT_CARDS"]]
            
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)