from .base import Notifier
from .dapnet import DapnetNotifier
from .pushover import PushoverNotifier

# Register new services here: config key -> class
REGISTRY = {
    "pushover": PushoverNotifier,
    "dapnet": DapnetNotifier,
}


def build_notifiers(cfg: dict):
    out = []
    for name, ncfg in cfg.get("notifiers", {}).items():
        if not ncfg.get("enabled", True):
            continue
        cls = REGISTRY.get(name)
        if cls is None:
            raise ValueError(f"Unknown notifier '{name}'. Known: {', '.join(REGISTRY)}")
        out.append(cls(ncfg))
    return out
