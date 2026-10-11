import requests

from .base import Notifier


class PushoverNotifier(Notifier):
    name = "pushover"

    def __init__(self, cfg):
        super().__init__(cfg)
        for k in ("app_token", "user_key"):
            if not cfg.get(k):
                raise ValueError(f"pushover: '{k}' is required")
        self.api_url = cfg.get("api_url", "https://api.pushover.net/1/messages.json")

    def send(self, alert):
        data = {
            "token": self.cfg["app_token"],
            "user": self.cfg["user_key"],
            "title": alert.title(),
            "message": alert.long_text(),
            "priority": int(self.cfg.get("priority", 0)),
        }
        if self.cfg.get("device"):
            data["device"] = self.cfg["device"]
        if self.cfg.get("sound"):
            data["sound"] = self.cfg["sound"]
        r = requests.post(self.api_url, data=data, timeout=15)
        r.raise_for_status()
