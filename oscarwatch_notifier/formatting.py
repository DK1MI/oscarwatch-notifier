"""Turn a passAlert message into human-readable notification text."""
from datetime import datetime, timezone


def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _hhmm_utc(ts):
    return _parse(ts).astimezone(timezone.utc).strftime("%H:%M")


def _local(ts):
    return _parse(ts).astimezone().strftime("%H:%M")


def _mins(seconds):
    s = int(seconds)
    return f"{round(s / 60)} min" if s >= 60 else f"{max(s, 0)} s"


class PassAlert:
    def __init__(self, msg: dict):
        p = msg["pass"]
        sat = p.get("satellite", {})
        self.name = sat.get("name", "Unknown")
        self.norad = sat.get("noradId", "")
        self.aos = p["aosUtc"]
        self.los = p["losUtc"]
        self.max_el = float(p.get("maxElevationDeg", 0))
        self.seconds_until_aos = p.get("secondsUntilAos")
        self.key = (self.norad or self.name, self.aos)

    def duration_s(self):
        return int((_parse(self.los) - _parse(self.aos)).total_seconds())

    def title(self):
        eta = f" in {_mins(self.seconds_until_aos)}" if self.seconds_until_aos is not None else ""
        return f"Satellite pass: {self.name}{eta}"

    def long_text(self):
        d = self.duration_s()
        lines = [
            f"{self.name} (NORAD {self.norad})",
            f"AOS: {_hhmm_utc(self.aos)} UTC ({_local(self.aos)} local)",
            f"LOS: {_hhmm_utc(self.los)} UTC ({_local(self.los)} local)",
            f"Max elevation: {self.max_el:.1f}°",
            f"Duration: {d // 60}m {d % 60:02d}s",
        ]
        return "\n".join(lines)

    def short_text(self, limit=80):
        """Compact text for pagers (DAPNET messages are limited to ~80 chars)."""
        eta = f" in {_mins(self.seconds_until_aos)}" if self.seconds_until_aos is not None else ""
        t = f"{self.name}{eta} AOS {_hhmm_utc(self.aos)} LOS {_hhmm_utc(self.los)}Z El {self.max_el:.0f}deg"
        return t[:limit]


def make_test_message() -> dict:
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {"type": "passAlert", "pass": {
        "satellite": {"name": "TEST-SAT", "noradId": "00000"},
        "aosUtc": fmt(now + timedelta(minutes=5)),
        "losUtc": fmt(now + timedelta(minutes=13)),
        "maxElevationDeg": 42.0, "secondsUntilAos": 300}}
