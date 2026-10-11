import argparse
import asyncio
import json
import logging

import websockets

from . import __version__
from .config import DEFAULT_PORT, load_config
from .formatting import PassAlert
from .notifiers import build_notifiers

log = logging.getLogger("passalert")


class Dispatcher:
    def __init__(self, notifiers, dedupe=True):
        self.notifiers = notifiers
        self.dedupe = dedupe
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
                continue
            if self.dedupe:
                if alert.key in self.seen:
                    log.debug("Duplicate passAlert for %s, skipped", alert.key)
                    continue
                self.seen.add(alert.key)
                if len(self.seen) > 1000:
                    self.seen.clear()
            log.info("passAlert: %s", alert.short_text())
            await self.dispatch(alert)

    async def dispatch(self, alert):
        async def one(n):
            try:
                await asyncio.to_thread(n.send, alert)
                log.info("[%s] notification sent", n.name)
            except Exception as e:  # one failing service must not block the others
                log.error("[%s] failed: %s", n.name, e)

        await asyncio.gather(*(one(n) for n in self.notifiers))


async def run(url, dispatcher):
    delay = 1
    while True:
        try:
            log.info("Connecting to %s", url)
            async with websockets.connect(url, ping_interval=20, max_size=None) as ws:
                log.info("Connected")
                delay = 1
                async for message in ws:
                    if isinstance(message, bytes):
                        message = message.decode("utf-8", "replace")
                    await dispatcher.handle_text(message)
            log.warning("Connection closed")
        except (OSError, websockets.exceptions.WebSocketException) as e:
            log.warning("Connection error: %s", e)
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
    ap.add_argument("--test", action="store_true", help="send a test notification and exit")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    cfg = load_config(args.config, args.url, args.host, args.port)
    notifiers = build_notifiers(cfg)
    if not notifiers:
        log.warning("No notifiers enabled (config: %s)", cfg["_path"])
    dispatcher = Dispatcher(notifiers, cfg.get("dedupe", True))

    if args.test:
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        msg = {"type": "passAlert", "pass": {
            "satellite": {"name": "TEST-SAT", "noradId": "00000"},
            "aosUtc": fmt(now + timedelta(minutes=5)),
            "losUtc": fmt(now + timedelta(minutes=13)),
            "maxElevationDeg": 42.0, "secondsUntilAos": 300}}
        asyncio.run(dispatcher.handle_text(json.dumps(msg)))
        return

    url = cfg["websocket"]["url"]
    try:
        asyncio.run(run(url, dispatcher))
    except KeyboardInterrupt:
        pass
