#!/usr/bin/env python3
"""
Anki Booster - Instalador Multi-OS
Copia os arquivos para pastas padrão de cada sistema, instala dependências,
instala a extensão e configura autostart.
"""
import sys, os, json, platform, shutil, subprocess
from pathlib import Path

# ───────────────── CONFIGURAÇÃO ─────────────────
APP_NAME = "Anki_Booster"
DATA_FOLDER = "anki_booster"
CONFIG_FILE = os.path.join(DATA_FOLDER, "anki_booster_config.json")

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
    "HIDE_FURIGANA_ON_HOVER": False  # Oculta furigana até passar o mouse sobre a palavra no popup
}

def log(msg, status="ℹ️"):
    print(f"{status} {msg}", flush=True)

# ───────────────── PATHS POR SO ─────────────────
def get_install_dir():
    home = Path.home()
    system = platform.system()
    if system == "Linux":
        return home / ".local" / "bin" / APP_NAME
    elif system == "Windows":
        appdata = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        return appdata / APP_NAME
    elif system == "Darwin":
        return home / "Applications" / APP_NAME
    return home / APP_NAME

def get_anki_addons_dir():
    system = platform.system()
    home = Path.home()
    if system == "Linux":
        flatpak = home / ".var" / "app" / "net.ankiweb.Anki" / "data" / "Anki2" / "addons21"
        return flatpak if flatpak.exists() else home / ".local" / "share" / "Anki2" / "addons21"
    elif system == "Windows":
        return Path(os.environ.get("APPDATA", home / "AppData" / "Roaming")) / "Anki2" / "addons21"
    elif system == "Darwin":
        return home / "Library" / "Application Support" / "Anki2" / "addons21"
    return None

# ───────────────── INSTALAÇÃO ─────────────────
def main():
    # 0. Verificação mínima de versão
    if sys.version_info < (3, 8):
        log("❌ Python 3.8+ necessário. Instale a versão mais recente e tente novamente.", "🔴")
        return 1

    log(f"🚀 Instalando {APP_NAME}", "🔹")
    print("=" * 50)
    
    src_dir = Path(__file__).parent.resolve()
    dst_dir = get_install_dir()
    log(f"📁 Origem: {src_dir}", "🔸")
    log(f"📦 Destino: {dst_dir}", "🔸")
    
    # 1. Criar pasta de destino
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        log("✅ Pasta de destino pronta", "🟢")
    except PermissionError:
        log("❌ Permissão negada. Execute com sudo/administrador se necessário.", "🔴")
        return 1

    # 2. Arquivos/Pastas para copiar
    items_to_copy = [
        "booster_service.py", "booster_utils.py", "theme.qml",
        "autostart.py", "anki_booster.vbs", "requirements.txt", "anki_extension",
        "sounds"
    ]
    
    copied = 0
    for item in items_to_copy:
        src_item = src_dir / item
        if not src_item.exists():
            log(f"⚠️ {item} não encontrado na origem. Pulando.", "🟡")
            continue
        
        dst_item = dst_dir / item
        try:
            if src_item.is_dir():
                if dst_item.exists(): shutil.rmtree(dst_item)
                shutil.copytree(src_item, dst_item)
            else:
                shutil.copy2(src_item, dst_item)
            log(f"📄 Copiado: {item}", "🟢")
            copied += 1
        except Exception as e:
            log(f"❌ Erro ao copiar {item}: {e}", "🔴")

    # 3. Pasta de dados local
    data_dir = dst_dir / DATA_FOLDER
    data_dir.mkdir(exist_ok=True)
    log(f"✅ Pasta de dados criada: {DATA_FOLDER}", "🟢")

    # 4. Config padrão (com log de debug)
    config_path = dst_dir / CONFIG_FILE
    log(f"🔍 Verificando config em: {config_path}", "🔸")
    
    if config_path.exists():
        log(f"✅ Config existente encontrada ({config_path.stat().st_size} bytes) → MANTIDA", "🟢")
    else:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        log("⚙️  Config padrão gerada", "🟢")

    # 5. Instalar dependências Python automaticamente
    req_file = dst_dir / "requirements.txt"
    if req_file.exists():
        log("📦 Instalando dependências (PyQt6)...", "🔸")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--quiet"],
                check=True
            )
            log("✅ Dependências instaladas com sucesso!", "🟢")
        except subprocess.CalledProcessError:
            log("⚠️ Falha ao instalar dependências. Rode manualmente: pip install -r requirements.txt", "🟡")
        except Exception as e:
            log(f"❌ Erro inesperado ao instalar deps: {e}", "🔴")

    # 6. Permissões (Linux/macOS)
    if platform.system() != "Windows":
        for script in ["booster_service.py", "autostart.py"]:
            p = dst_dir / script
            if p.exists(): p.chmod(0o755)
        log("🔐 Permissões de execução definidas", "🟢")

    # 7. Instalar Extensão no Anki
    ext_src = dst_dir / "anki_extension"
    addons_dir = get_anki_addons_dir()
    if ext_src.exists() and addons_dir and addons_dir.exists():
        ext_dst = addons_dir / "Anki Booster"
        try:
            if ext_dst.exists(): shutil.rmtree(ext_dst)
            shutil.copytree(ext_src, ext_dst)
            log(f"✅ Extensão instalada: {ext_dst}", "🟢")
        except Exception as e:
            log(f"⚠️ Falha ao copiar extensão (Anki aberto ou permissão?): {e}", "🟡")
    elif addons_dir is None or not addons_dir.exists():
        log("⚠️ Pasta addons21 do Anki não encontrada. Instale o Anki primeiro.", "🟡")
    else:
        log("ℹ️ Pasta anki_extension não encontrada. Pulando.", "🟡")

    # 8. Autostart
    autostart_script = dst_dir / "autostart.py"
    if autostart_script.exists():
        print("\n" + "="*50)
        try:
            resp = input("🔔 Iniciar automaticamente com o sistema? [y/N]: ").strip().lower()
            if resp in ("y", "sim", "s", "yes", "1"):
                log("⚙️ Configurando autostart...", "🔸")
                subprocess.run([sys.executable, str(autostart_script), "enable"], cwd=dst_dir, check=True)
                log("✅ Autostart ativado!", "🟢")
            else:
                log("⏭️ Autostart ignorado.", "🟡")
        except (EOFError, KeyboardInterrupt):
            log("⏭️ Input não interativo ou cancelado. Autostart ignorado.", "🟡")
        except Exception as e:
            log(f"⚠️ Falha no autostart: {e}", "🟡")
    else:
        log("ℹ️ autostart.py não encontrado. Pulando.", "🟡")

    # 9. Resumo
    print("\n" + "=" * 50)
    log(f"✅ Instalação concluída! ({copied} itens copiados)", "🟢")
    print(f"\n📂 Local de instalação: {dst_dir}")
    print(f"📂 Dados do app: {dst_dir / DATA_FOLDER}")
    print(f"\n👉 Para rodar manualmente:")
    if platform.system() == "Windows":
        print(f"   cd /d \"{dst_dir}\" && python booster_service.py")
    else:
        print(f"   cd {dst_dir} && python3 booster_service.py")
    print(f"\n💡 Dica: Use o mesmo ZIP para atualizar futuramente.")
    return 0

if __name__ == "__main__":
    
    sys.exit(main())