"""Configuration: JSON file, overridable by environment variables and CLI flags."""
import json
import os
from pathlib import Path

DEFAULT_PORT = 7373
DEFAULT_HOST = "localhost"


def default_config_path() -> Path:
    """Config next to the working dir if present, else the per-user config dir."""
    local = Path("config.json")
    if local.exists():
        return local
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif os.uname().sysname == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "oscarwatch-notifier" / "config.json"


def load_config(path, ws_url=None, host=None, port=None) -> dict:
    cfg = {"websocket": {}, "dedupe": True, "notifiers": {}}
    p = Path(path) if path else default_config_path()
    if p.exists():
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        cfg.update(data)
        cfg.setdefault("websocket", {})
        cfg.setdefault("notifiers", {})
    elif path:
        raise FileNotFoundError(f"Config file not found: {p}")
    cfg["_path"] = str(p)

    ws = cfg["websocket"]
    # Precedence: CLI > environment > config file > defaults
    ws_url = ws_url or os.environ.get("OSCARWATCH_WS_URL")
    host = host or os.environ.get("OSCARWATCH_WS_HOST") or ws.get("host")
    port = port or os.environ.get("OSCARWATCH_WS_PORT") or ws.get("port")
    if ws_url:
        ws["url"] = ws_url
    elif host or port or not ws.get("url"):
        ws["url"] = f"ws://{host or DEFAULT_HOST}:{int(port or DEFAULT_PORT)}"
    return cfg
