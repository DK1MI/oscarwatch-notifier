# oscarwatch-notifier

Small cross-platform (Linux, macOS, Windows) helper. Connects to a websocket, ignores everything except
`"type":"passAlert"` messages, and notifies **all enabled services** (currently Pushover and DAPNET/hampager.de).

![](/img/pager.jpg)

## How it works
oscarwatch-notifier connects to the websocket provided by the **OscarWatch** application, listens for
`passAlert` messages (an upcoming satellite pass) and forwards each one as a notification to every enabled service.
All other message types (e.g. `satelliteStatus`) are ignored.

## Prerequisite: enable "Satellite Link" in OscarWatch
> **Important:** OscarWatch does **not send any messages over the websocket** until the Satellite Link integration
> is enabled. Without it, oscarwatch-notifier will connect successfully but never receive a `passAlert`.

In OscarWatch, go to **Settings → Integrations → Satellite Link** and enable it. Make sure the websocket port
shown there matches the port configured here (default `7373`; see [Websocket configuration](#websocket-configuration-default-ws-localhost-7373)).

## Install & run
```
pip install -r requirements.txt          # Python 3.9+
cp config.example.json config.json       # fill in credentials
python -m oscarwatch_notifier             # or: -c path/to/config.json
python -m oscarwatch_notifier --test      # send a test notification and exit
```
Then open the web UI (see below) at http://localhost:8080.

## Troubleshooting
- **Status shows "connected" but no notifications arrive:** Satellite Link is probably not enabled in OscarWatch
  (Settings → Integrations → Satellite Link), or no pass is upcoming yet. Use "Send test notification" in the UI to
  verify the notification services independently.
- **Status shows "disconnected":** OscarWatch is not running, or the URL/port does not match. Check the websocket URL
  in the UI or config.
- **Pushover/DAPNET errors:** see the activity log in the UI for the HTTP error returned by the service.

## Web UI
On start the app serves a UI at **http://localhost:8080** (stdlib only, no extra dependencies): connection status,
live activity log, settings for websocket/Pushover/DAPNET (saved to config.json, applied immediately), and a
"Send test notification" button. Secrets are masked in the UI.

`--ui-port 9000`, `--ui-host 0.0.0.0` (⚠ no authentication - only on trusted networks), `--no-ui`;
or in config.json: `"ui": {"enabled": true, "host": "127.0.0.1", "port": 8080}`.
The app also starts without any notifier configured, so you can set everything up in the UI.

![](/img/webinterface.png)


## Websocket configuration (default `ws://localhost:7373`)
Precedence: CLI > environment > config file > default.

| Setting | CLI | Env | config.json (`websocket`) |
|---|---|---|---|
| Full URL | `--url ws://host:7373` | `OSCARWATCH_WS_URL` | `url` |
| Host | `--host` | `OSCARWATCH_WS_HOST` | `host` |
| Port | `--port` | `OSCARWATCH_WS_PORT` | `port` |

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
