#!/usr/bin/env python3
"""
Anki Booster - Logger Module
Sistema de logs modular: terminal colorido + buffer JSON + servidor HTTP.
Thread-safe, agrupamento inteligente, zero poluição.
"""
import os, sys, json, datetime, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Cores e emojis para terminal
_COLORS = {"INFO": "\033[94m", "OK": "\033[92m", "ERR": "\033[91m", "WARN": "\033[93m"}
_EMOJIS = {"INFO": "📘", "OK": "✅", "ERR": "❌", "WARN": "⚠️"}

class BoosterLogger:
    """Logger modular com buffer circular e servidor HTTP integrado"""
    
    def __init__(self, buffer_max: int = 200, port: int = 8895, script_dir: str = ""):
        self.buffer = []
        self.buffer_max = buffer_max
        self.port = port
        self.script_dir = script_dir
        self._server = None
        self._lock = threading.Lock()
    
    def log(self, msg: str, level: str = "INFO") -> None:
        """Loga no terminal E adiciona ao buffer (thread-safe)"""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        color = _COLORS.get(level, "\033[0m")
        emoji = _EMOJIS.get(level, "📝")
        
        # Terminal output
        print(f"{color}{emoji} [{now}] {msg}\033[0m", flush=True)
        
        # Buffer output (thread-safe)
        with self._lock:
            entry = {
                "timestamp": now,
                "level": level,
                "message": msg,
                "key": f"{level}:{msg}"  # Para agrupamento no frontend
            }
            self.buffer.append(entry)
            if len(self.buffer) > self.buffer_max:
                self.buffer.pop(0)
    
    def get_logs(self, limit: int = None) -> list:
        """Retorna cópia segura do buffer"""
        with self._lock:
            logs = self.buffer[-limit:] if limit else list(self.buffer)
        return logs
    
    def start_server(self, daemon: bool = True) -> None:
        """Inicia servidor HTTP para interface de logs"""
        logger_ref = self
        
        class LogHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/api/logs':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(logger_ref.get_logs()).encode('utf-8'))
                elif self.path in ('/', '/index.html'):
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    html_path = os.path.join(logger_ref.script_dir, 'booster_logs.html')
                    if os.path.exists(html_path):
                        with open(html_path, 'rb') as f:
                            self.wfile.write(f.read())
                else:
                    self.send_response(404)
                    self.end_headers()
            def log_message(self, *args): pass  # Silencia logs do HTTP
        
        self._server = HTTPServer(('127.0.0.1', self.port), LogHandler)
        thread = threading.Thread(target=self._server.serve_forever, daemon=daemon)
        thread.start()
        self.log(f"🌐 Logs disponíveis em http://127.0.0.1:{self.port}", "OK")
    
    def stop_server(self) -> None:
        """Para o servidor HTTP (cleanup)"""
        if self._server:
            self._server.shutdown()
