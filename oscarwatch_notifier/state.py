"""Shared runtime state, used by the websocket loop and the web UI thread."""
import asyncio
import json
import threading
import time
from collections import deque
from pathlib import Path

from .notifiers import build_notifiers

SECRET_MASK = "********"
SECRETS = {("pushover", "app_token"), ("pushover", "user_key"), ("dapnet", "password")}


class AppState:
    def __init__(self, cfg):
        self.lock = threading.RLock()
        self.cfg = cfg
        self.status = "connecting"
        self.status_detail = ""
        self.events = deque(maxlen=300)
        self.notifiers = []
        self.dedupe = cfg.get("dedupe", True)
        self.loop = None
        self.conn_task = None
        self.restart_requested = False
        self.dispatcher = None

    # ---- events / status
    def event(self, kind, text):
        with self.lock:
            self.events.append({"t": time.strftime("%H:%M:%S"), "kind": kind, "text": text})

    def set_status(self, status, detail=""):
        with self.lock:
            changed = (status, detail) != (self.status, self.status_detail)
            self.status, self.status_detail = status, detail
        if changed:
            self.event("info", f"{status}: {detail}" if detail else status)

    @property
    def url(self):
        return self.cfg["websocket"]["url"]

    def snapshot(self):
        with self.lock:
            return {"status": self.status, "detail": self.status_detail, "url": self.url,
                    "notifiers": [n.name for n in self.notifiers],
                    "events": list(self.events)}

    # ---- config
    def masked_config(self):
        with self.lock:
            out = json.loads(json.dumps({k: v for k, v in self.cfg.items() if not k.startswith("_")}))
        for svc, key in SECRETS:
            if out.get("notifiers", {}).get(svc, {}).get(key):
                out["notifiers"][svc][key] = SECRET_MASK
        return out

    def apply_config(self, new):
        """Validate, persist, hot-reload. Raises ValueError on invalid input."""
        with self.lock:
            merged = json.loads(json.dumps({k: v for k, v in self.cfg.items() if not k.startswith("_")}))
            url = (new.get("websocket", {}).get("url") or "").strip()
            if not url.startswith(("ws://", "wss://")):
                raise ValueError("Websocket URL must start with ws:// or wss://")
            ws = merged.setdefault("websocket", {})
            ws["url"] = url
            ws.pop("host", None)
            ws.pop("port", None)
            merged["dedupe"] = bool(new.get("dedupe", True))
            for svc, ncfg in new.get("notifiers", {}).items():
                cur = merged.setdefault("notifiers", {}).setdefault(svc, {})
                for k, v in ncfg.items():
                    if (svc, k) in SECRETS and v == SECRET_MASK:
                        continue
                    cur[k] = v
            notifiers = build_notifiers(merged)  # validates; may raise ValueError
            path = Path(self.cfg["_path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(merged, indent=2), encoding="utf-8")
            tmp.replace(path)
            try:
                path.chmod(0o600)  # contains credentials
            except OSError:
                pass
            url_changed = url != self.cfg["websocket"]["url"]
            path_s = self.cfg["_path"]
            self.cfg = merged
            self.cfg["_path"] = path_s
            self.notifiers = notifiers
            self.dedupe = merged["dedupe"]
        self.event("info", "Settings saved")
        if url_changed and self.loop and self.conn_task:
            self.restart_requested = True
            self.loop.call_soon_threadsafe(self.conn_task.cancel)
