#!/usr/bin/env python3
"""
🔧 Anki Booster - Utilitários (MODO: DEPENDENTE DO SERVICE)
Este módulo NÃO toma decisões. Apenas executa operações quando solicitado.
✅ Arquitetura: service como cérebro único; utils como braço executor.
"""
import os, sys, json, sqlite3, datetime, platform, pathlib, re, base64, shutil, tempfile, time
from typing import Optional, List, Dict, Any

# ───────────────── PATHS CROSS-PLATFORM ─────────────────
def get_script_dir() -> str:
    """Retorna o diretório onde o script está localizado"""
    return os.path.dirname(os.path.abspath(__file__))

def get_anki_base_path() -> str:
    """Retorna o caminho base do Anki conforme o SO (Linux/Flatpak robusto)"""
    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
        return os.path.join(appdata, "Anki2")
    
    # Linux: verifica caminhos Flatpak conhecidos (ordem de prioridade)
    flatpak_paths = [
        os.path.expanduser("~/.var/app/net.ankiweb.Anki/data/Anki2"),
        os.path.expanduser("~/.var/app/io.github.anki/data/Anki2"),
        os.path.expanduser("~/.var/app/com.anki/data/Anki2"),
    ]
    
    for path in flatpak_paths:
        if os.path.isdir(path):
            # log(f"📍 Flatpak Anki detectado: {path}", "INFO")
            return path
            
    # Fallback: caminho nativo (instalação via pip/appimage/repos)
    native = os.path.expanduser("~/.local/share/Anki2")
    if os.path.isdir(native):
        return native
        
    # Se nenhum existir, retorna o Flatpak oficial para logging claro
    log("⚠️ Nenhum diretório Anki2 encontrado. Verifique se o Anki já foi aberto ao menos uma vez.", "WARN")
    return flatpak_paths[0]

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
BASE_ANKI = get_anki_base_path()

# ───────────────── LOG UTILS ─────────────────
def log(msg: str, level: str = "INFO") -> None:
    """Log colorido com emoji e timestamp"""
    colors = {"INFO": "\033[94m", "OK": "\033[92m", "ERR": "\033[91m", "WARN": "\033[93m"}
    emojis = {"INFO": "📘", "OK": "✅", "ERR": "❌", "WARN": "⚠️"}
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"{colors[level]}{emojis[level]} [{now}] {msg}\033[0m", flush=True)

# ───────────────── JSON UTILS ─────────────────
def load_json_file(path: str, default: Any) -> Any:
    """Carrega JSON com fallback e logging de erro"""
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"⚠️ Erro ao ler JSON {path}: {e}", "WARN")
    return default

def save_json_file(path: str, data: Any) -> None:
    """Salva JSON com criação de diretório"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ───────────────── CONFIG LOADER (✅ ADICIONADO DE VOLTA) ─────────────────
def load_config() -> Dict[str, Any]:
    """
    Carrega config do arquivo ou retorna dict vazio.
    ✅ Service aplica defaults → utils não decide valores padrão.
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding='utf-8') as f:
                loaded = json.load(f)
                log(f"📄 Config carregada: {CONFIG_FILE}", "INFO")
                return loaded
        except json.JSONDecodeError as e:
            log(f"❌ JSON inválido em {CONFIG_FILE}: {e}", "ERR")
        except PermissionError:
            log(f"❌ Sem permissão para ler {CONFIG_FILE}", "ERR")
        except Exception as e:
            log(f"❌ Erro ao carregar config: {type(e).__name__}: {e}", "ERR")
    return {}  # Service aplica defaults

# ───────────────── FAVORITOS (SQLite local) ─────────────────
# ✅ Apenas operações CRUD. Sem lógica de negócio.
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
def _wrap_html(content: str, starred: bool, level: int, consecutive: int, 
               fav_thresholds: Dict[int, int], hide_furigana: bool) -> str:
    """
    Envolve o conteúdo do card com CSS e indicadores.
    ✅ fav_thresholds vem do service → UI sempre alinhada com backend.
    """
    star_html = "⭐" if starred else ""
    # ✅ Usa thresholds do service para exibir progresso correto
    required = fav_thresholds.get(level, 5)
    level_html = f" <span style='font-size:12px;color:#ffd700'>[N{level}: {consecutive}/{required}]</span>" if starred else ""
    
    hide_scrollbar_css = """
    <style>
        html, body { margin: 0; padding: 0; height: 100%; overflow-y: auto !important; overflow-x: hidden !important; scrollbar-width: none !important; }
        ::-webkit-scrollbar { display: none !important; }
    </style>
    """
    
    furigana_css = ""
    if hide_furigana:
        furigana_css = """
        <style>
        ruby rt {
            opacity: 0 !important;
            transition: opacity 0.15s ease;
            pointer-events: none;
        }
        ruby:hover rt {
            opacity: 1 !important;
        }
        /* Em telas touch, mantém sempre visível */
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

# ───────────────── MEDIA PARSER ─────────────────
def _parse_anki_media(text: str, media_dir: Optional[str]) -> str:
    """
    Converte tags [sound:xxx.mp3] do Anki para <audio> HTML5 embutido em Base64.
    ✅ FIX: prefixo `data:` adicionado para funcionar no WebView
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
                
                # ✅ FIX CRÍTICO: prefixo `data:` para data URI funcionar
                return f'<audio controls src="data:{mime};base64,{b64}"></audio>'
            except Exception as e:
                log(f"⚠️ Erro ao ler áudio {filename}: {e}", "WARN")
                return f'<span style="color:red; font-size:12px">[Audio: {filename}]</span>'
        
        return match.group(0)

    return re.sub(r'\[sound:([^\]]+)\]', replace_audio, text, flags=re.IGNORECASE)

# ───────────────── CARD LOADER ─────────────────
def load_cards_from_anki(
    anki_db_path: str,
    favs: List[str],
    state: Dict[str, Any],
    daily: Dict[str, Any],
    # ✅ Filtros decididos pelo service (utils não decide nada):
    revlog_days: int,
    revlog_types: List[int],
    limit_cards: int,
    front_fields: Optional[List[int]],
    back_fields: Optional[List[int]],
) -> List[Dict[str, Any]]:
    """
    Carrega cards brutos do Anki.
    ✅ NÃO filtra por next_due, limites ou favoritos.
    ✅ Retorna cards brutos para o service decidir o que fazer.
    """
    log(f"📂 Lendo Anki: {revlog_days}d, tipos={revlog_types}, limite={limit_cards}...")
    temp_dir = None
    
    try:
        temp_dir = tempfile.mkdtemp(prefix="anki_booster_")
        temp_db = os.path.join(temp_dir, "collection.anki2")
        
        if not os.path.exists(anki_db_path):
            log(f"❌ DB do Anki não encontrado: {anki_db_path}", "ERR")
            return []
            
        shutil.copy2(anki_db_path, temp_db)
        cutoff = int((time.time() - revlog_days * 86400) * 1000)  # 86400 = 24*60*60
        conn = sqlite3.connect(temp_db)

        # Query: Favoritos (se houver)
        fav_raw, fav_ints = [], []
        if favs:
            try:
                fav_ints = [int(f) for f in favs]
            except ValueError:
                fav_ints = []
            if fav_ints:
                placeholders = ','.join('?' * len(fav_ints))
                fav_raw = conn.execute(
                    f"SELECT DISTINCT c.id, n.flds, n.mid FROM cards c JOIN notes n ON c.nid = n.id WHERE c.id IN ({placeholders})",
                    fav_ints
                ).fetchall()

        # Query: Não-favoritos com revlog recente
        # ✅ SQL seguro com placeholders parameterizados
        revlog_placeholders = ','.join('?' * len(revlog_types))
        exclude_clause = f"AND c.id NOT IN ({','.join(['?']*len(fav_ints))})" if fav_ints else ""
        
        query = f"""
            SELECT DISTINCT c.id, n.flds, n.mid 
            FROM cards c 
            JOIN notes n ON c.nid = n.id 
            JOIN revlog r ON c.id = r.cid 
            WHERE r.id > ? AND r.type IN ({revlog_placeholders}) {exclude_clause}
        """
        
        # ✅ Parâmetros na ordem correta: cutoff, revlog_types..., fav_ints...
        params = (cutoff, *revlog_types, *fav_ints) if fav_ints else (cutoff, *revlog_types)
        non_fav_raw = conn.execute(query, params).fetchall()

        # Extrai modelos (para fallback de campos quando front_fields/back_fields são None)
        models_map = {}
        try:
            col_data = conn.execute("SELECT models FROM col").fetchone()
            if col_data and col_data[0]:
                models = json.loads(col_data[0])
                for mid_str, model in models.items():
                    mid_val = int(mid_str)
                    fld_names = [f['name'] for f in model.get('flds', [])]
                    qfmt = model.get('tmpls', [{}])[0].get('qfmt', '')
                    # Regex para extrair nomes de campos usados no template
                    used = set(re.findall(r'\{[\{#^]?\s*(?:[\w]+:)?\s*([^\s{}]+?)\s*[\}]?\}', qfmt))
                    f_idx = [i for i, n in enumerate(fld_names) if n in used] or [0]
                    b_idx = [i for i in range(len(fld_names)) if i not in f_idx] or list(range(len(fld_names)))
                    models_map[mid_val] = (f_idx, b_idx)
        except Exception as e:
            log(f"⚠️ Falha ao ler modelos do Anki: {e}", "WARN")

        conn.close()
        
        # Combina e deduplica
        raw = fav_raw + non_fav_raw
        seen = set()
        unique = [(cid, flds, mid) for cid, flds, mid in raw if cid not in seen and not seen.add(cid)]

        MEDIA_DIR = os.path.join(os.path.dirname(anki_db_path), "collection.media")
        cards = []
        
        for cid, flds, mid_val in unique:
            all_f = flds.split("\x1f")
            s = state.get(str(cid), {})
            
            # ✅ Lógica de campos: service decide, utils executa
            # - front_fields/back_fields = None → usa fallback do modelo
            # - front_fields/back_fields = [] → usa [0] (primeiro campo) como fallback seguro
            # - front_fields/back_fields = [1,2] → usa esses índices exatos
            if front_fields is not None:
                f_idx = front_fields if front_fields else [0]
            else:
                f_idx = models_map.get(mid_val, ([0], None))[0]
            
            if back_fields is not None:
                b_idx = back_fields if back_fields else list(range(len(all_f)))
            else:
                b_idx = models_map.get(mid_val, ([0], list(range(len(all_f)))))[1]
            
            # Monta HTML com parsing de mídia
            front_parts = [all_f[i] for i in f_idx if 0 <= i < len(all_f) and all_f[i].strip()]
            back_parts = [all_f[i] for i in b_idx if 0 <= i < len(all_f) and all_f[i].strip()]
            
            front_html = "<br>".join(_parse_anki_media(f, MEDIA_DIR) for f in front_parts)
            back_html = "<br>".join(_parse_anki_media(f, MEDIA_DIR) for f in back_parts)

            cards.append({
                "id": cid,
                "front": front_html,
                "back": back_html,
                # ✅ Estado vem do service, não é calculado aqui
                "streak": s.get("streak", 0),
                "errors_recent": s.get("errors_recent", 0),
                "fav_level": s.get("fav_level", 1),
                "fav_consecutive": s.get("fav_consecutive", 0),
                "next_due": float(s.get("next_due", 0))
            })

        # ✅ SEM FILTRO DE next_due, SEM FILTRO DE LIMITE DIÁRIO
        # O service decide o que é elegível. Aqui só retornamos os brutos.
        return cards[:limit_cards]  # Apenas limite global de segurança
            
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
