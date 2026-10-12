import requests

from .base import Notifier


class DapnetNotifier(Notifier):
    """DAPNET / hampager.de pager call via the HTTP API."""
    name = "dapnet"

    def __init__(self, cfg):
        super().__init__(cfg)
        for k in ("username", "password"):
            if not cfg.get(k):
                raise ValueError(f"dapnet: '{k}' is required")
        if not cfg.get("callsigns"):
            raise ValueError("dapnet: 'callsigns' must list at least one destination")
        if not cfg.get("transmitter_groups"):
            raise ValueError("dapnet: 'transmitter_groups' must list at least one group")
        # Internet default; use http://dapnet.db0sda.hamnet.radio:8080/calls on HAMNET
        self.url = cfg.get("url", "http://hampager.de/api/calls")

    def send(self, alert):
        payload = {
            "text": alert.short_text(),
            "callSignNames": self.cfg["callsigns"],
            "transmitterGroupNames": self.cfg["transmitter_groups"],
            "emergency": bool(self.cfg.get("emergency", False)),
        }
        r = requests.post(
            self.url,
            json=payload,
            auth=(self.cfg["username"], self.cfg["password"]),
            timeout=15,
        )
        r.raise_for_status()
