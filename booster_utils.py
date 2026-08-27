#!/usr/bin/env python3
"""
🔧 Anki Booster - Utilitários (MODO: DEPENDENTE DO SERVICE)
Este módulo NÃO toma decisões. Apenas executa operações quando solicitado.
Arquitetura: service como cérebro único; utils como braço executor.

CHANGELOG DESTA REVISÃO:
1. load_cards_from_anki(): parsing de 'favs' -> 'fav_ints' agora ignora
   individualmente cids malformados, em vez de descartar TODOS os
   favoritos quando um único item não é conversível para int.
2. generate_anki_report(): cabeçalho realinhado com as colunas
   realmente escritas no corpo (antes "RATIO"/"EASE"/etc. apontavam
   para os campos errados).
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

    flatpak_paths = [
        os.path.expanduser("~/.var/app/net.ankiweb.Anki/data/Anki2"),
        os.path.expanduser("~/.var/app/io.github.anki/data/Anki2"),
        os.path.expanduser("~/.var/app/com.anki/data/Anki2"),
    ]

    for path in flatpak_paths:
        if os.path.isdir(path):
            return path

    native = os.path.expanduser("~/.local/share/Anki2")
    if os.path.isdir(native):
        return native

    log("⚠️ Nenhum diretório Anki2 encontrado. Verifique se o Anki já foi aberto ao menos uma vez.", "WARN")
    return flatpak_paths[0]

SCRIPT_DIR = get_script_dir()
BOOSTER_DATA_DIR = os.path.join(SCRIPT_DIR, "anki_booster")
os.makedirs(BOOSTER_DATA_DIR, exist_ok=True)

STATE_FILE = os.path.join(BOOSTER_DATA_DIR, "anki_booster_state.json")
DAILY_FILE = os.path.join(BOOSTER_DATA_DIR, "anki_booster_daily.json")
DB_FILE = os.path.join(BOOSTER_DATA_DIR, "anki_booster.db")
CONFIG_FILE = os.path.join(BOOSTER_DATA_DIR, "anki_booster_config.json")
CMD_PORT = 8894
BASE_ANKI = get_anki_base_path()
_logger_ref = None

# ───────────────── LOG UTILS ─────────────────

def set_logger(logger):
    global _logger_ref
    _logger_ref = logger

def log(msg: str, level: str = "INFO") -> None:
    if _logger_ref and hasattr(_logger_ref, 'log'):
        _logger_ref.log(msg, level)
    else:
        colors = {"INFO": "\033[94m", "OK": "\033[92m", "ERR": "\033[91m", "WARN": "\033[93m"}
        emojis = {"INFO": "📘", "OK": "", "ERR": "❌", "WARN": "⚠️"}
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"{colors[level]}{emojis[level]} [{now}] {msg}\033[0m", flush=True)

# ───────────────── THEME UTILS ─────────────────
THEMES_FILE = os.path.join(SCRIPT_DIR, "themes.json")

def load_theme() -> dict:
    fallback = {
        "bg": "#fafafa", "surface": "#ffffff", "text": "#2d3748",
        "accent": "#ffb4a8", "accentText": "#561e16"
    }
    if not os.path.exists(THEMES_FILE):
        return fallback
    try:
        with open(THEMES_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        theme_name = cfg.get("default", "light")
        return cfg.get(theme_name, cfg.get("light", fallback))
    except Exception as e:
        log(f"⚠️ Erro ao carregar tema: {e}", "WARN")
        return fallback

def set_theme(theme_name: str) -> bool:
    if not os.path.exists(THEMES_FILE): return False
    try:
        with open(THEMES_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if theme_name in cfg:
            cfg["default"] = theme_name
            with open(THEMES_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            log(f"🎨 Tema salvo: {theme_name}", "OK")
            return True
        return False
    except Exception as e:
        log(f"❌ Erro ao salvar tema: {e}", "ERR")
        return False

# ───────────────── JSON UTILS ─────────────────
def load_json_file(path: str, default: Any) -> Any:
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"⚠️ Erro ao ler JSON {path}: {e}", "WARN")
    return default

def save_json_file(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ───────────────── CONFIG LOADER ─────────────────
def load_config() -> Dict[str, Any]:
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
    return {}

# ───────────────── FAVORITOS (SQLite local) ─────────────────
_fav_conn: Optional[sqlite3.Connection] = None

def _get_fav_conn() -> sqlite3.Connection:
    global _fav_conn
    if _fav_conn is None:
        _fav_conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        _fav_conn.execute("CREATE TABLE IF NOT EXISTS favs (cid TEXT PRIMARY KEY)")
        _fav_conn.commit()
    return _fav_conn

def get_all_favs() -> List[str]:
    conn = _get_fav_conn()
    return [r[0] for r in conn.execute("SELECT cid FROM favs")]

def toggle_fav(cid: str) -> List[str]:
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
    conn = _get_fav_conn()
    conn.execute("DELETE FROM favs WHERE cid=?", (cid,))
    conn.commit()
    log(f"🎓 Favorito {cid} GRADUADO!", "OK")

# ───────────────── CHECK ANKI ─────────────────
def get_anki_db() -> Optional[str]:
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
    # ANTES: quando o card não era favorito, o span da estrela ficava
    # vazio ("") - nada aparecia. Agora sempre existe uma estrela: cheia
    # e brilhando (⭐, com filter/drop-shadow + pulso) se favorito, ou
    # contorno apagado (☆, sem brilho, sem animação) se não - dá pra
    # sempre ver onde clicar pra favoritar, mesmo em cards não-favoritos.
    star_glyph = "⭐" if starred else "☆"
    star_css_class = "oboete-star-on" if starred else "oboete-star-off"
    required = fav_thresholds.get(level, 5)
    level_html = f" <span style='font-size:12px;color:#ffd700'>[N{level}: {consecutive}/{required}]</span>" if starred else ""

    hide_scrollbar_css = """
    <style>
        html, body { margin: 0; padding: 0; height: 100%; overflow-y: auto !important; overflow-x: hidden !important; scrollbar-width: none !important; }
        ::-webkit-scrollbar { display: none !important; }
    </style>
    """

    # NOVO: CSS da estrela de favorito.
    # .oboete-star-on  -> cheia, dourada, brilho (drop-shadow) e pulso
    #                     suave contínuo (chama atenção sem ser irritante).
    # .oboete-star-off -> contorno vazio, opaca/apagada, sem brilho, sem
    #                     animação - só um indicador discreto e clicável.
    # .oboete-star-pop -> animação de "pulo" de ~0.35s disparada via JS
    #                     (theme.qml) no exato momento do clique, dando
    #                     feedback imediato de que o toggle funcionou.
    fav_star_css = """
    <style>
        #oboete-fav-star {
            display: inline-block;
            transition: color 0.2s ease, opacity 0.2s ease, filter 0.2s ease;
        }
        .oboete-star-on {
            color: gold;
            opacity: 1;
            filter: drop-shadow(0 0 4px gold);
            animation: oboete-star-pulse 1.8s ease-in-out infinite;
        }
        .oboete-star-off {
            color: currentColor;
            opacity: 0.35;
            filter: none;
            animation: none;
        }
        .oboete-star-pop {
            animation: oboete-star-pop 0.35s ease-out !important;
        }
        @keyframes oboete-star-pulse {
            0%   { transform: scale(1); }
            50%  { transform: scale(1.15); }
            100% { transform: scale(1); }
        }
        @keyframes oboete-star-pop {
            0%   { transform: scale(1); }
            40%  { transform: scale(1.5); }
            100% { transform: scale(1); }
        }
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
        @media (hover: none) {
            ruby rt { opacity: 1 !important; }
        }
        </style>
        """

    return f"""
    {hide_scrollbar_css}
    {fav_star_css}
    {furigana_css}
    <div style="text-align:center;line-height:1.5;padding:10px;min-height:100vh;display:flex;align-items:center;justify-content:center;box-sizing:border-box;">
        <div style="position:absolute;top:8px;right:12px;font-size:20px;">
            <span id="oboete-fav-star" class="{star_css_class}">{star_glyph}</span><span id="oboete-fav-level">{level_html}</span>
        </div>
        <div style="display:inline-block;text-align:center;max-width:100%;">
            {content}
        </div>
    </div>
    """

# ───────────────── MEDIA PARSER ─────────────────
def _parse_anki_media(text: str, media_dir: Optional[str]) -> str:
    if not text or not media_dir:
        return text

    def replace_media(match):
        tag = match.group(0)
        src_match = re.search(r'(?:sound:|src=")([^"\]]+)', tag)
        if not src_match: return tag

        filename = src_match.group(1).strip().replace('\\', '/')
        filepath = os.path.join(media_dir, filename)

        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')

                ext = os.path.splitext(filename)[1].lower()
                mime_map = {
                    '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.wav': 'audio/wav', '.flac': 'audio/flac',
                    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif',
                    '.webp': 'image/webp', '.svg': 'image/svg+xml', '.bmp': 'image/bmp'
                }
                mime = mime_map.get(ext, 'application/octet-stream')

                if tag.startswith('[sound:'):
                    return f'<audio controls src="data:{mime};base64,{b64}"></audio>'
                else:
                    return f'<img src="data:{mime};base64,{b64}" style="max-width:100%;height:auto;">'
            except Exception as e:
                log(f"⚠️ Erro ao carregar mídia {filename}: {e}", "WARN")
                return tag
        return tag

    text = re.sub(r'\[sound:([^\]]+)\]', replace_media, text, flags=re.IGNORECASE)
    text = re.sub(r'<img\b[^>]*src=["\']([^"\']+)["\'][^>]*>', replace_media, text, flags=re.IGNORECASE)
    return text

# ───────────────── CARD LOADER ─────────────────
def load_cards_from_anki(
    anki_db_path: str,
    favs: List[str],
    state: Dict[str, Any],
    daily: Dict[str, Any],
    revlog_days: int,
    revlog_types: List[int],
    limit_cards: int,
    front_fields: Optional[List[int]],
    back_fields: Optional[List[int]],
) -> List[Dict[str, Any]]:
    """
    Carrega cards brutos do Anki.
    NÃO filtra por next_due, limites ou favoritos.
    Retorna cards brutos para o service decidir o que fazer.
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
        cutoff = int((time.time() - revlog_days * 86400) * 1000)
        conn = sqlite3.connect(temp_db)

        revlog_subquery = """
            SELECT cid,
                COUNT(*) as total_reps,
                SUM(CASE WHEN ease = 1 THEN 1 ELSE 0 END) as revlog_lapses,
                SUM(CASE WHEN type = 1 THEN 1 ELSE 0 END) as revlog_hard,
                SUM(CASE WHEN type = 2 THEN 1 ELSE 0 END) as revlog_good,
                SUM(CASE WHEN type = 3 THEN 1 ELSE 0 END) as revlog_easy,
                AVG(factor) as avg_ease_factor,
                MAX(id) as last_review_ts
            FROM revlog
            WHERE id > ?
            GROUP BY cid
        """

        # FIX: antes, se UM único cid em 'favs' não fosse conversível para
        # int, TODOS os favoritos eram descartados (fav_ints = []). Agora
        # cada item inválido é ignorado individualmente e logado.
        fav_raw, fav_ints = [], []
        if favs:
            for f in favs:
                try:
                    fav_ints.append(int(f))
                except (ValueError, TypeError):
                    log(f"⚠️ Favorito com cid inválido ignorado: {f!r}", "WARN")
            if fav_ints:
                placeholders = ','.join('?' * len(fav_ints))
                fav_query = f"""
                    SELECT c.id, n.flds, n.mid,
                        c.lapses, c.factor, c.ivl, c.type,
                        COALESCE(r.total_reps, 0), COALESCE(r.revlog_lapses, 0),
                        COALESCE(r.revlog_hard, 0), COALESCE(r.revlog_good, 0),
                        COALESCE(r.revlog_easy, 0), COALESCE(r.avg_ease_factor, 0),
                        COALESCE(r.last_review_ts, 0)
                    FROM cards c JOIN notes n ON c.nid = n.id
                    LEFT JOIN ({revlog_subquery}) r ON c.id = r.cid
                    WHERE c.id IN ({placeholders})
                """
                fav_raw = conn.execute(fav_query, (cutoff, *fav_ints)).fetchall()

        revlog_placeholders = ','.join('?' * len(revlog_types))
        exclude_clause = f"AND c.id NOT IN ({','.join(['?']*len(fav_ints))})" if fav_ints else ""

        non_fav_query = f"""
            SELECT c.id, n.flds, n.mid,
                c.lapses, c.factor, c.ivl, c.type,
                COALESCE(r.total_reps, 0), COALESCE(r.revlog_lapses, 0),
                COALESCE(r.revlog_hard, 0), COALESCE(r.revlog_good, 0),
                COALESCE(r.revlog_easy, 0), COALESCE(r.avg_ease_factor, 0),
                COALESCE(r.last_review_ts, 0)
            FROM cards c JOIN notes n ON c.nid = n.id
            LEFT JOIN ({revlog_subquery}) r ON c.id = r.cid
            WHERE c.id IN (
                SELECT DISTINCT cid FROM revlog WHERE id > ? AND type IN ({revlog_placeholders}) {exclude_clause}
            )
        """
        params = (cutoff, cutoff, *revlog_types, *fav_ints) if fav_ints else (cutoff, cutoff, *revlog_types)
        non_fav_raw = conn.execute(non_fav_query, params).fetchall()

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

        raw = fav_raw + non_fav_raw
        seen = set()
        unique = [row for row in raw if row[0] not in seen and not seen.add(row[0])]

        MEDIA_DIR = os.path.join(os.path.dirname(anki_db_path), "collection.media")
        cards = []

        for row in unique:
            cid, flds, mid_val = row[0], row[1], row[2]
            anki_lapses = row[3] or 0
            anki_factor = row[4] or 2500
            anki_ease = anki_factor / 10
            anki_interval = row[5] or 0
            card_type = row[6] or 0
            total_reps = row[7] or 0
            revlog_lapses = row[8] or 0
            avg_ease_factor = row[12] or 0
            last_review_ts = row[13] or 0

            all_f = flds.split("\x1f")
            s = state.get(str(cid), {})

            if front_fields is not None:
                f_idx = front_fields if front_fields else [0]
            else:
                f_idx = models_map.get(mid_val, ([0], None))[0]

            if back_fields is not None:
                b_idx = back_fields if back_fields else list(range(len(all_f)))
            else:
                b_idx = models_map.get(mid_val, ([0], list(range(len(all_f)))))[1]

            front_parts = [all_f[i] for i in f_idx if 0 <= i < len(all_f) and all_f[i].strip()]
            back_parts = [all_f[i] for i in b_idx if 0 <= i < len(all_f) and all_f[i].strip()]

            front_html = "<br>".join(_parse_anki_media(f, MEDIA_DIR) for f in front_parts)
            back_html = "<br>".join(_parse_anki_media(f, MEDIA_DIR) for f in back_parts)

            lapse_ratio = (revlog_lapses / total_reps) if total_reps > 0 else 0.0

            cards.append({
                "id": cid,
                "front": front_html,
                "back": back_html,
                "streak": s.get("streak", 0),
                "errors_recent": s.get("errors_recent", 0),
                "fav_level": s.get("fav_level", 1),
                "fav_consecutive": s.get("fav_consecutive", 0),
                "next_due": float(s.get("next_due", 0)),
                "anki_lapses": anki_lapses,
                "anki_ease": anki_ease,
                "anki_factor": anki_factor,
                "anki_interval": anki_interval,
                "anki_card_type": card_type,
                "anki_total_reps": total_reps,
                "anki_revlog_lapses": revlog_lapses,
                "anki_lapse_ratio": lapse_ratio,
                "anki_last_review": last_review_ts,
                "anki_avg_ease_factor": avg_ease_factor
            })

        return cards[:limit_cards]

    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

def generate_anki_report(cards, output_path):
    """
    FIX: o cabeçalho antigo dizia
        ID | LAPSOS | RATIO | EASE | IVL | ERROS_RECENTES | STREAK | FRENTE
    mas o corpo escrevia, nessa ordem:
        id, anki_lapses, anki_revlog_lapses, anki_total_reps,
        anki_lapse_ratio, anki_ease, anki_interval, front
    ou seja, a partir da 3ª coluna tudo ficava deslocado (onde o cabeçalho
    prometia "RATIO" vinha revlog_lapses, onde prometia "EASE" vinha
    total_reps, etc.), e ERROS_RECENTES/STREAK nunca eram escritos.
    Agora o cabeçalho bate exatamente com as colunas reais do corpo.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(
            "ID | LAPSOS_ANKI | LAPSOS_REVLOG | TOTAL_REPS | RATIO | EASE | IVL | FRENTE\n"
        )
        f.write("=" * 180 + "\n")

        for c in cards:
            front = re.sub(r"<[^>]+>", "", c.get("front", "")).strip()

            f.write(
                f"{c['id']} | "
                f"{c.get('anki_lapses',0)} | "
                f"{c.get('anki_revlog_lapses',0)} | "
                f"{c.get('anki_total_reps',0)} | "
                f"{c.get('anki_lapse_ratio',0):.2f} | "
                f"{c.get('anki_ease',250):.0f} | "
                f"{c.get('anki_interval',0)} | "
                f"{front[:80]}\n"
            )
