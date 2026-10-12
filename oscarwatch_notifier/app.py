import argparse
import asyncio
import json
import logging

import websockets

from . import __version__
from .config import DEFAULT_PORT, load_config
from .formatting import PassAlert, make_test_message
from .notifiers import build_notifiers
from .state import AppState

log = logging.getLogger("oscarwatch")


class Dispatcher:
    def __init__(self, state: AppState):
        self.state = state
        self.seen = set()

    async def handle_text(self, text: str):
        # A frame may carry several newline-separated JSON objects.
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                log.debug("Ignoring non-JSON line: %.80s", line)
                continue
            if not isinstance(msg, dict) or msg.get("type") != "passAlert":
                continue
            try:
                alert = PassAlert(msg)
            except (KeyError, ValueError, TypeError) as e:
                log.warning("Malformed passAlert (%s): %.200s", e, line)
                self.state.event("error", f"Malformed passAlert: {e}")
                continue
            if self.state.dedupe:
                if alert.key in self.seen:
                    log.debug("Duplicate passAlert for %s, skipped", alert.key)
                    continue
                self.seen.add(alert.key)
                if len(self.seen) > 1000:
                    self.seen.clear()
            log.info("passAlert: %s", alert.short_text())
            self.state.event("alert", alert.short_text())
            await self.dispatch(alert)

    async def dispatch(self, alert):
        """Send to all enabled services in parallel. Returns [{name, ok, error}]."""
        async def one(n):
            try:
                await asyncio.to_thread(n.send, alert)
                log.info("[%s] notification sent", n.name)
                self.state.event("notify", f"[{n.name}] sent")
                return {"name": n.name, "ok": True}
            except Exception as e:  # one failing service must not block the others
                log.error("[%s] failed: %s", n.name, e)
                self.state.event("error", f"[{n.name}] failed: {e}")
                return {"name": n.name, "ok": False, "error": str(e)}

        return list(await asyncio.gather(*(one(n) for n in list(self.state.notifiers))))


async def session(state, dispatcher):
    """One connection attempt. Returns True if the connection was established."""
    url = state.url
    connected = False
    try:
        log.info("Connecting to %s", url)
        async with websockets.connect(url, ping_interval=20, max_size=None) as ws:
            connected = True
            log.info("Connected")
            state.set_status("connected", url)
            async for message in ws:
                if isinstance(message, bytes):
                    message = message.decode("utf-8", "replace")
                await dispatcher.handle_text(message)
        state.set_status("disconnected", "connection closed")
    except (OSError, websockets.exceptions.WebSocketException, ValueError) as e:
        log.warning("Connection error: %s", e)
        state.set_status("disconnected", str(e))
    return connected


async def run(state, dispatcher):
    state.loop = asyncio.get_running_loop()
    state.dispatcher = dispatcher
    delay = 1
    while True:
        state.set_status("connecting", state.url)
        task = asyncio.create_task(session(state, dispatcher))
        state.conn_task = task
        try:
            await asyncio.wait({task})
        finally:
            if not task.done():
                task.cancel()
        if task.cancelled():
            if state.restart_requested:  # URL changed in the UI
                state.restart_requested = False
                delay = 1
                continue
            return
        if task.result():
            delay = 1
        log.info("Reconnecting in %ds", delay)
        await asyncio.sleep(delay)
        delay = min(delay * 2, 30)


def main():
    ap = argparse.ArgumentParser(
        prog="oscarwatch-notifier",
        description="Listen on a websocket for passAlert messages and send notifications.",
    )
    ap.add_argument("-c", "--config", help="path to config.json")
    ap.add_argument("--url", help="full websocket URL (e.g. ws://192.168.1.5:7373)")
    ap.add_argument("--host", help="websocket host (default: localhost)")
    ap.add_argument("--port", type=int, help=f"websocket port (default: {DEFAULT_PORT})")
    ap.add_argument("--ui-host", help="web UI bind address (default: 127.0.0.1)")
    ap.add_argument("--ui-port", type=int, help="web UI port (default: 8080)")
    ap.add_argument("--no-ui", action="store_true", help="disable the web UI")
    ap.add_argument("--test", action="store_true", help="send a test notification and exit")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    cfg = load_config(args.config, args.url, args.host, args.port)
    state = AppState(cfg)
    ui_cfg = cfg.get("ui", {})
    ui_enabled = not args.no_ui and ui_cfg.get("enabled", True)
    try:
        state.notifiers = build_notifiers(cfg)
    except ValueError as e:
        if not ui_enabled or args.test:
            raise SystemExit(f"Configuration error: {e}")
        log.error("Configuration error: %s (fix it in the web UI)", e)
    if not state.notifiers:
        log.warning("No notifiers enabled (config: %s)", cfg["_path"])
    dispatcher = Dispatcher(state)

    if args.test:
        results = asyncio.run(dispatcher.dispatch(PassAlert(make_test_message())))
        for r in results:
            print(r)
        return

    if ui_enabled:
        from .web import start_web
        host = args.ui_host or ui_cfg.get("host", "127.0.0.1")
        port = args.ui_port or int(ui_cfg.get("port", 8080))
        try:
            start_web(state, host, port)
        except OSError as e:
            raise SystemExit(f"Cannot start web UI on {host}:{port}: {e}")

    try:
        asyncio.run(run(state, dispatcher))
    except KeyboardInterrupt:
        pass
