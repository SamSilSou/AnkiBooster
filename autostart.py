#!/usr/bin/env python3
"""
Anki Booster - Autostart Setup (Cross-OS + Reinício Automático)
Uso: python autostart.py [enable|disable]
"""
import sys, os, platform, subprocess
from pathlib import Path

def get_paths():
    python_exe = sys.executable
    service_script = str(Path(__file__).parent.resolve() / "booster_service.py")
    return python_exe, service_script

# ───────────────── LINUX (systemd --user) ─────────────────
# ───────────────── LINUX (systemd --user) ─────────────────
def enable_linux(python_exe, service_script):
    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    service_file = service_dir / "anki-booster.service"

    content = f"""[Unit]
Description=Anki Booster Service
After=default.target

[Service]
Type=simple
ExecStart="{python_exe}" "{service_script}"
Restart=always
RestartSec=3
# 🛡️ Variáveis para travar resize no Wayland/Hyprland
Environment="QT_WAYLAND_RESIZE_ON_CONTENT_CHANGE=0"
Environment="QT_QPA_PLATFORM=wayland"

[Install]
WantedBy=default.target
"""
    service_file.write_text(content, encoding="utf-8")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "anki-booster.service"], check=True)
    print("✅ Linux: systemd service ativado (reinicia ao fechar + vars Wayland)")

def disable_linux():
    subprocess.run(["systemctl", "--user", "disable", "--now", "anki-booster.service"], check=False)
    service_file = Path.home() / ".config" / "systemd" / "user" / "anki-booster.service"
    if service_file.exists(): service_file.unlink()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    print("🗑️ Linux: Autostart removido")

# ───────────────── WINDOWS (Startup .vbs com caminho absoluto) ─────────────────
def enable_windows(python_exe, service_script):
    startup = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup.mkdir(parents=True, exist_ok=True)
    vbs = startup / "anki_booster.vbs"
    
    # Template do VBS com placeholders {script_path} e {python_exe}, responsavel por reiniciar o serviço 
    vbs_template = '''\
' anki_booster.vbs - Autostart silencioso (gerado automaticamente)
Dim fso, shell, scriptPath, scriptDir
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

' Caminhos absolutos injetados pelo autostart.py
scriptPath = "{script_path}"
scriptDir = fso.GetParentFolderName(scriptPath)

' Define diretório de trabalho para a pasta do booster (imports relativos funcionam)
shell.CurrentDirectory = scriptDir

' Loop infinito: reinicia sempre que o booster fechar
Do
    ' 0 = janela oculta, True = espera o processo terminar
    shell.Run "{python_exe} """ & scriptPath & """", 0, True
    WScript.Sleep 3000
Loop
'''
    
    #  Injeta os caminhos reais usando .format() (evita conflito de aspas)
    vbs_content = vbs_template.format(
        script_path=service_script,
        python_exe=python_exe
    )
    
    vbs.write_text(vbs_content, encoding="utf-8")
    
    # Limpa arquivos antigos (.bat ou .vbs anterior)
    for ext in [".bat", ".vbs"]:
        old = startup / f"anki_booster{ext}"
        if old.exists() and old != vbs: 
            old.unlink()
    
    print("✅ Windows: .vbs criado na Startup (caminho absoluto + silencioso + reinício)")

def disable_windows():
    for ext in [".vbs", ".bat"]:
        file = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"anki_booster{ext}"
        if file.exists(): file.unlink()
    print("🗑️ Windows: Autostart removido")

# ───────────────── MACOS (LaunchAgents + KeepAlive) ─────────────────
def enable_macos(python_exe, service_script):
    plist_dir = Path.home() / "Library" / "LaunchAgents"
    plist_dir.mkdir(parents=True, exist_ok=True)
    plist = plist_dir / "com.ankibooster.service.plist"

    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ankibooster.service</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_exe}</string>
        <string>{service_script}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
    <key>StandardOutPath</key>
    <string>/tmp/anki_booster.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/anki_booster.log</string>
</dict>
</plist>"""
    plist.write_text(content, encoding="utf-8")
    print("✅ macOS: LaunchAgent ativado (KeepAlive: reinicia ao fechar)")

def disable_macos():
    plist = Path.home() / "Library" / "LaunchAgents" / "com.ankibooster.service.plist"
    if plist.exists():
        subprocess.run(["launchctl", "unload", str(plist)], check=False)
        plist.unlink()
    print("🗑️ macOS: Autostart removido")

# ───────────────── MAIN ─────────────────
def main():
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "enable"
    if action not in ("enable", "disable"):
        print("Uso: python autostart.py [enable|disable]")
        sys.exit(1)

    python_exe, service_script = get_paths()
    system = platform.system()

    try:
        if system == "Linux":
            enable_linux(python_exe, service_script) if action == "enable" else disable_linux()
        elif system == "Windows":
            enable_windows(python_exe, service_script) if action == "enable" else disable_windows()
        elif system == "Darwin":
            enable_macos(python_exe, service_script) if action == "enable" else disable_macos()
        else:
            print("❌ SO não suportado")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao configurar autostart: {e}")
        sys.exit(1)
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    
    #    No Linux/macOS rodando no terminal, só aperta Enter e segue a vida
    if exit_code == 0:
        try:
            input("\n✅ Autostart configurado, pressione Enter para continuar")
        except (EOFError, KeyboardInterrupt):
            pass  # Ignora se rodando em pipe/script não-interativo
    
    sys.exit(exit_code)