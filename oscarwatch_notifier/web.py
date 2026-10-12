"""Tiny built-in web UI (stdlib only)."""
import asyncio
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import __version__
from .formatting import PassAlert, make_test_message
from .ui_html import INDEX_HTML

log = logging.getLogger("oscarwatch.web")
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def make_handler(state, restrict_host):
    class Handler(BaseHTTPRequestHandler):
        server_version = f"oscarwatch/{__version__}"

        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj))

        def _host_ok(self):
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
            if restrict_host and host not in LOOPBACK:  # DNS-rebinding protection
                return False
            origin = self.headers.get("Origin")
            if origin and self.command == "POST":
                if urlparse(origin).netloc != self.headers.get("Host"):
                    return False
            return True

        def do_GET(self):
            if not self._host_ok():
                return self._json(403, {"error": "forbidden"})
            path = urlparse(self.path).path
            if path == "/":
                self._send(200, INDEX_HTML.replace("__VERSION__", __version__), "text/html")
            elif path == "/api/status":
                self._json(200, state.snapshot())
            elif path == "/api/config":
                self._json(200, state.masked_config())
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._host_ok():
                return self._json(403, {"error": "forbidden"})
            if "application/json" not in (self.headers.get("Content-Type") or ""):
                return self._json(415, {"error": "JSON required"})
            path = urlparse(self.path).path
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
            except (ValueError, json.JSONDecodeError):
                return self._json(400, {"error": "invalid JSON"})
            if path == "/api/config":
                try:
                    state.apply_config(body)
                except ValueError as e:
                    return self._json(400, {"error": str(e)})
                except OSError as e:
                    return self._json(500, {"error": f"Could not write config: {e}"})
                self._json(200, {"ok": True})
            elif path == "/api/test":
                if not state.loop or not state.dispatcher:
                    return self._json(503, {"error": "not ready"})
                alert = PassAlert(make_test_message())
                fut = asyncio.run_coroutine_threadsafe(state.dispatcher.dispatch(alert), state.loop)
                try:
                    results = fut.result(45)
                except Exception as e:
                    return self._json(500, {"error": str(e)})
                self._json(200, {"results": results})
            else:
                self._json(404, {"error": "not found"})

    return Handler


def start_web(state, host, port):
    handler = make_handler(state, restrict_host=host in LOOPBACK)
    srv = ThreadingHTTPServer((host, port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True, name="web-ui").start()
    shown = "localhost" if host in ("127.0.0.1", "0.0.0.0") else host
    log.info("Web UI: http://%s:%d", shown, port)
    if host not in LOOPBACK:
        log.warning("Web UI is reachable from the network and has NO authentication.")
    return srv
