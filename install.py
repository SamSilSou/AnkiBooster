#!/usr/bin/env python3
"""
Anki Booster - Instalador Multi-OS
Copia os arquivos para pastas padrão de cada sistema, cria um venv
ISOLADO para as dependências (não mexe no Python do sistema), instala
a extensão e configura autostart.

CHANGELOG DESTA REVISÃO:
- NOVO: em vez de rodar `pip install` no Python do sistema (que pode
  falhar em distros com PEP 668 / "externally-managed-environment", e
  de qualquer forma polui o Python global do usuário), o instalador
  agora cria um venv dedicado dentro da própria pasta de instalação
  (dst_dir/venv) e instala as dependências ali dentro.
- O "para rodar manualmente" no resumo final agora aponta pro Python
  do venv, não pro Python do sistema.
- O autostart (quando habilitado) é configurado a partir do Python do
  venv, então se autostart.py usar sys.executable internamente pra
  montar o comando de inicialização, ele vai gravar o caminho do venv
  automaticamente - o serviço volta a rodar isolado mesmo no boot.
"""
from __future__ import annotations
import sys, os, json, platform, shutil, subprocess, venv
from pathlib import Path

# ───────────────── CONFIGURAÇÃO ─────────────────
APP_NAME = "Anki_Booster"
DATA_FOLDER = "anki_booster"
CONFIG_FILE = os.path.join(DATA_FOLDER, "anki_booster_config.json")
VENV_FOLDER = "venv"

# ───────────────── CONFIG PADRÃO ─────────────────
DEFAULT_CONFIG = {
    "GLOBAL_CORRECT": 1200,
    "GLOBAL_WRONG": 300,
    "BUFFER_SIZE": 5,
    "MAX_DAILY": 3,
    "REVLOG_DAYS": 3,
    "LIMIT_CARDS": 15,
    "FAVS_PRIORITY": 3,
    "REVLOG_TYPES": [0, 1, 2, 3],
    "FRONT_FIELDS": None,
    "BACK_FIELDS": None,
    "MIN_CARD_DELAY": 20,
    "HIDE_FURIGANA_ON_HOVER": True  # Oculta furigana até passar o mouse sobre a palavra no popup
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

def get_venv_python(venv_dir: Path) -> Path:
    """Caminho do executável Python DENTRO do venv, por SO."""
    if platform.system() == "Windows":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python3"

def get_venv_pip(venv_dir: Path) -> Path:
    """Caminho do pip DENTRO do venv, por SO."""
    if platform.system() == "Windows":
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip3"

def _pip_is_functional(venv_python: Path) -> bool:
    """
    Confirma de verdade que `python -m pip` funciona dentro do venv, em
    vez de assumir isso só porque o binário do Python existe. É essa
    checagem que faltava antes: víamos "venv_python.exists()" e
    declarávamos sucesso, mesmo quando o venv existe mas o pip nunca foi
    instalado nele (ver _bootstrap_pip_via_getpip).
    """
    try:
        r = subprocess.run(
            [str(venv_python), "-m", "pip", "--version"],
            capture_output=True, text=True, timeout=15
        )
        return r.returncode == 0
    except Exception:
        return False

def _bootstrap_pip_via_getpip(venv_python: Path, venv_dir: Path) -> bool:
    """
    Workaround para um problema conhecido em distros Debian/Ubuntu: o
    pacote `python3-venv` da distro remove os wheels do pip que o
    ensurepip normalmente usaria, então `venv.EnvBuilder(with_pip=True)`
    cria o venv normalmente (o Python existe, o venv "parece" válido),
    mas o pip simplesmente não vem instalado dentro - `python3 -m pip`
    falha com "No module named pip".

    Aqui baixamos o script oficial get-pip.py (a mesma fonte que o
    ensurepip usaria por baixo dos panos) e rodamos com o Python DE
    DENTRO do venv, instalando o pip isoladamente ali - sem tocar no
    Python do sistema nem precisar de sudo/apt.
    """
    import urllib.request
    get_pip_path = venv_dir / "get-pip.py"
    try:
        log("🌐 pip ausente no venv - baixando get-pip.py para reparar...", "🔸")
        urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", str(get_pip_path))
    except Exception as e:
        log(f"⚠️ Falha ao baixar get-pip.py (sem internet?): {e}", "🟡")
        return False

    try:
        subprocess.run(
            [str(venv_python), str(get_pip_path), "--quiet"],
            check=True, timeout=120
        )
    except Exception as e:
        log(f"⚠️ Falha ao rodar get-pip.py: {e}", "🟡")
        return False
    finally:
        try:
            get_pip_path.unlink(missing_ok=True)
        except Exception:
            pass

    return _pip_is_functional(venv_python)

def create_venv(dst_dir: Path) -> Path | None:
    """
    Cria (ou reaproveita, se já existir e tiver pip FUNCIONAL - não só
    "o binário existe") um venv isolado dentro de dst_dir/venv. Retorna
    o Path do Python do venv, ou None se não for possível deixar o pip
    funcionando (nesse caso o instalador cai pro fallback do Python do
    sistema, avisando o usuário).
    """
    venv_dir = dst_dir / VENV_FOLDER
    venv_python = get_venv_python(venv_dir)

    if venv_python.exists():
        # FIX: antes bastava o binário existir pra reaproveitar o venv
        # cegamente. Agora confirma que o pip REALMENTE funciona - senão
        # tenta reparar via get-pip.py antes de desistir.
        if _pip_is_functional(venv_python):
            log(f"♻️  Venv já existe e tem pip funcional, reaproveitando: {venv_dir}", "🟢")
            return venv_python
        log("⚠️ Venv existente sem pip funcional (comum em distros Debian/Ubuntu, "
            "onde python3-venv vem sem o ensurepip). Tentando reparar...", "🟡")
        if _bootstrap_pip_via_getpip(venv_python, venv_dir):
            log("✅ pip reparado dentro do venv existente", "🟢")
            return venv_python
        log("⚠️ Não foi possível reparar o pip do venv existente.", "🟡")
        return None

    log(f"🐍 Criando venv isolado em: {venv_dir}", "🔸")
    try:
        # with_pip=True tenta instalar o pip já na criação. Funciona na
        # maioria dos casos (Windows, macOS, Fedora, Arch...), mas pode
        # "ter sucesso" sem pip funcional em Debian/Ubuntu (ver abaixo).
        venv.EnvBuilder(with_pip=True, clear=False).create(str(venv_dir))
    except Exception as e:
        log(f"⚠️ Falha ao criar venv com pip embutido: {e}", "🟡")
        log("🔁 Tentando criar o venv sem pip embutido, pra reparar depois...", "🔸")
        try:
            venv.EnvBuilder(with_pip=False, clear=True).create(str(venv_dir))
        except Exception as e2:
            log(f"⚠️ Falha ao criar venv mesmo sem pip: {e2}", "🟡")
            return None

    if not venv_python.exists():
        log("⚠️ Venv criado, mas o Python esperado não apareceu no caminho previsto.", "🟡")
        return None

    if _pip_is_functional(venv_python):
        log("✅ Venv criado com sucesso (pip já funcional)", "🟢")
        return venv_python

    # Este é o caso do seu log: venv "criado com sucesso" (o Python
    # existe), mas "No module named pip" ao tentar usar - típico de
    # Debian/Ubuntu com ensurepip removido do pacote python3-venv.
    log("⚠️ Venv criado, mas SEM pip funcional (comum em Debian/Ubuntu - "
        "o pacote python3-venv da distro vem sem o módulo ensurepip). "
        "Tentando reparar baixando get-pip.py...", "🟡")
    if _bootstrap_pip_via_getpip(venv_python, venv_dir):
        log("✅ pip instalado via bootstrap (get-pip.py)", "🟢")
        return venv_python

    log("⚠️ Não foi possível instalar o pip no venv automaticamente.", "🟡")
    log("   Correção manual (Debian/Ubuntu): sudo apt install python3-venv python3-pip", "🟡")
    log(f"   Ou rode: curl -sS https://bootstrap.pypa.io/get-pip.py | {venv_python}", "🟡")
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
        "sounds", "booster_tray.py", "rocket.gif", "icon.svg", "booster_logger.py", "booster_logs.html", "themes.json"
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

    # 5. Criar venv isolado e instalar dependências ali dentro
    #    (em vez de instalar no Python do sistema, evitando conflito com
    #    outros pacotes/projetos e contornando restrições tipo PEP 668
    #    em distros Linux modernas).
    venv_python = create_venv(dst_dir)

    req_file = dst_dir / "requirements.txt"
    if req_file.exists():
        if venv_python is not None:
            log("📦 Instalando dependências (PyQt6) dentro do venv...", "🔸")
            try:
                subprocess.run(
                    [str(venv_python), "-m", "pip", "install", "-r", str(req_file), "--quiet"],
                    check=True
                )
                log("✅ Dependências instaladas no venv com sucesso!", "🟢")
            except subprocess.CalledProcessError:
                log("⚠️ Falha ao instalar dependências no venv.", "🟡")
                log(f"   Rode manualmente: {venv_python} -m pip install -r {req_file}", "🟡")
            except Exception as e:
                log(f"❌ Erro inesperado ao instalar deps no venv: {e}", "🔴")
        else:
            # Fallback: venv não pôde ser criado. Avisa claramente que vai
            # cair no Python do sistema, em vez de falhar silenciosamente.
            log("⚠️ Venv indisponível - instalando no Python do SISTEMA como fallback.", "🟡")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--quiet"],
                    check=True
                )
                log("✅ Dependências instaladas no Python do sistema (fallback).", "🟢")
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
                # NOVO: roda autostart.py usando o Python do VENV (se
                # disponível), não o do sistema. Se autostart.py monta o
                # comando de inicialização usando sys.executable
                # internamente, isso já grava o caminho do venv - o
                # serviço volta a iniciar isolado mesmo no boot, sem
                # precisar de nenhuma mudança em autostart.py.
                autostart_python = venv_python if venv_python is not None else sys.executable
                subprocess.run([str(autostart_python), str(autostart_script), "enable"], cwd=dst_dir, check=True)
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
    if venv_python is not None:
        print(f"🐍 Venv isolado: {dst_dir / VENV_FOLDER}")
    print(f"\n👉 Para rodar manualmente:")
    if venv_python is not None:
        if platform.system() == "Windows":
            print(f"   cd /d \"{dst_dir}\" && \"{venv_python}\" booster_service.py")
        else:
            print(f"   cd {dst_dir} && {venv_python} booster_service.py")
    else:
        log("⚠️ Rodando sem venv (fallback pro Python do sistema).", "🟡")
        if platform.system() == "Windows":
            print(f"   cd /d \"{dst_dir}\" && python booster_service.py")
        else:
            print(f"   cd {dst_dir} && python3 booster_service.py")
    print(f"\n💡 Dica: Use o mesmo ZIP para atualizar futuramente (o venv é reaproveitado, não recriado do zero).")
    return 0

if __name__ == "__main__":

    sys.exit(main())
