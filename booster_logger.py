#!/usr/bin/env python3
"""
📓 Anki Booster - Logger Module (VERSÃO ESTÁVEL)
"""
import os, sys, json, datetime, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

_COLORS = {"INFO": "\033[94m", "OK": "\033[92m", "ERR": "\033[91m", "WARN": "\033[93m"}
_EMOJIS = {"INFO": "📘", "OK": "✅", "ERR": "❌", "WARN": "⚠️"}

class BoosterLogger:
    def __init__(self, buffer_max=200, port=8895, script_dir=""):
        self.buffer = []
        self.buffer_max = buffer_max
        self.port = port
        self.script_dir = os.path.abspath(script_dir) if script_dir else os.getcwd()
        self._server = None
        self._lock = threading.Lock()

    def log(self, msg: str, level: str = "INFO", to_terminal: bool = True) -> None:
        """Log com opção de imprimir no terminal (padrão: True)"""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        
        # ✅ Imprime no terminal se to_terminal=True (padrão)
        if to_terminal:
            color = _COLORS.get(level, "\033[0m")
            emoji = _EMOJIS.get(level, "📝")
            print(f"{color}{emoji} [{now}] {msg}\033[0m", flush=True)
        
        # ✅ Sempre adiciona ao buffer para a interface web
        with self._lock:
            self.buffer.append({
                "timestamp": now,
                "level": level,
                "message": msg,
                "key": f"{level}:{msg}"
            })
            if len(self.buffer) > self.buffer_max:
                self.buffer.pop(0)

    def get_logs(self) -> list:
        with self._lock:
            return list(self.buffer)

    def start_server(self, daemon: bool = True) -> None:
        """Inicia servidor HTTP em thread separada"""
        logger_ref = self
        
        class LogHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = self.path.split('?')[0]  # Remove ?t=...
                
                # API JSON
                if path == '/api/logs':
                    with logger_ref._lock:
                        data = json.dumps(logger_ref.buffer).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(data)
                    return
                
                # HTML booster_logger.html (prioritário)
                if path in ('/', '/karaoke', '/booster_logs.html'):
                    self._serve_file('booster_logs.html')
                    return
                
                # HTML Padrão
                if path in ('/logs', '/booster_logs.html'):
                    self._serve_file('booster_logs.html')
                    return
                
                # 404
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'404 - Rota nao encontrada')

            def _serve_file(self, filename):
                filepath = os.path.join(logger_ref.script_dir, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    self.send_response(404)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(f'404 - Arquivo nao encontrado: {filename}'.encode())

            def log_message(self, *args): pass  # Silencia logs padrão do HTTP

        # ✅ Inicia servidor em thread daemon (não bloqueia o service)
        try:
            self._server = HTTPServer(('127.0.0.1', self.port), LogHandler)
            # Log de inicialização VISÍVEL
            print(f"✅ Logger HTTP rodando em http://127.0.0.1:{self.port}", flush=True)
            thread = threading.Thread(target=self._server.serve_forever, daemon=daemon)
            thread.start()
        except OSError as e:
            if e.errno == 98:  # Address already in use
                print(f"⚠️ Porta {self.port} em uso, usando existente", flush=True)
            else:
                raise

    def stop_server(self):
        if self._server:
            self._server.shutdown()
