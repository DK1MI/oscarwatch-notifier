class Notifier:
    """Base class. Implement send() (blocking; called in a worker thread)."""
    name = "base"

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def send(self, alert) -> None:
        raise NotImplementedError
