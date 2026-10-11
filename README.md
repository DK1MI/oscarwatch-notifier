# oscarwatch-notifier

Small cross-platform (Linux, macOS, Windows) helper. Connects to a websocket, ignores everything except
`"type":"passAlert"` messages, and notifies **all enabled services** (currently Pushover and DAPNET).

![](/img/pager.jpg)

## Install & run
```
pip install -r requirements.txt          # Python 3.9+
cp config.example.json config.json       # fill in credentials
python -m oscarwatch_notifier             # or: -c path/to/config.json
python -m oscarwatch_notifier --test      # send a test notification and exit
```

## Websocket configuration (default `ws://localhost:7373`)

In order to receive messages from OscarWatch, enable "Satellite Link" in OscarWatch's **Settings -> Integrations -> Satellite Link**.

Configure the URL with the IP address of the system on which OscarWatch is running and the port that you have configured in the integrations setup (default is 7373).

Precedence: CLI > environment > config file > default.

| Setting | CLI | Env | config.json (`websocket`) |
|---|---|---|---|
| Full URL | `--url ws://host:7373` | `PASSALERT_WS_URL` | `url` |
| Host | `--host` | `PASSALERT_WS_HOST` | `host` |
| Port | `--port` | `PASSALERT_WS_PORT` | `port` |

Reconnects automatically (backoff up to 30 s). Config is read from `./config.json` or the per-user config dir
(`~/.config/oscarwatch-notifier`, `~/Library/Application Support/oscarwatch-notifier`, `%APPDATA%\oscarwatch-notifier`).
`dedupe: true` (default) suppresses repeated alerts for the same satellite + AOS time.

## Notifiers
- **Pushover**: `app_token`, `user_key`, optional `device`, `priority`, `sound`.
- **DAPNET**: `username`, `password`, `callsigns[]`, `transmitter_groups[]`, `emergency`, `url`
  (default `http://hampager.de/api/calls`; HAMNET: `http://dapnet.db0sda.hamnet.radio:8080/calls`).
  Text is compacted to 80 chars, e.g. `AO-73 in 5 min AOS 16:14 LOS 16:22Z El 9deg`.

Add a service: create a `Notifier` subclass in `oscarwatch_notifier/notifiers/` and register it in `__init__.py`.
A failing service never blocks the others.

## Single executable (optional)
`pip install pyinstaller && pyinstaller --onefile -n oscarwatch-notifier oscarwatch_notifier/__main__.py`
(run on each target OS).
