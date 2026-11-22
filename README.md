# report-failed-services

Notifies a Discord channel of systemd services in the Failed state. It also sends a recovery notification once a previously notified service is no longer Failed.

## Requirements

- Linux with systemd (`systemctl` and `journalctl`)
- Python 3.10+
- Dependencies in [requirements.txt](requirements.txt): `python-dotenv`, `requests`
- A Discord Bot token and the ID of the channel the bot posts to

## Installation

1. Clone the repository: `git clone https://github.com/book000/report-failed-services.git`
2. Create a virtual environment named `venv` in the repository root and install the dependencies: `python3 -m venv venv && venv/bin/pip install -U -r requirements.txt`
3. Create the configuration file `.env` (see Configuration below).
4. Register the systemd unit and timer: `bash SystemdFiles/install-systemd.sh`

The installer rewrites `SystemdFiles/report-failed-services.service` in place with the repository path (do not commit that change; to move the repository, restore the file with `git checkout` and run the installer again), copies the service and timer files to `/etc/systemd/system/` with `sudo`, then enables and starts the timer.
The service runs `venv/bin/python -m src` as root, so the virtual environment from step 2 is required.
The timer runs it every 30 minutes (at minutes 00 and 30).

Each Discord request times out after 5 seconds to connect or 15 seconds without a response, and systemd stops a run that takes longer than 10 minutes (`TimeoutStartSec=600`), so a stalled request cannot block later timer runs.
Each service is processed independently: a journal-read or notification failure leaves that notification pending and processing continues with later failures and recoveries. Failed sends do not add failure state or remove recovery state. If any service remains unsuccessful, the run logs a summary and exits with status 1; a fully successful run exits with status 0.

Discord HTTP 429 and 5xx responses are retried up to three total attempts per notification, with at most 30 seconds of retry waiting per notification. For 429 responses, the tool honors Discord's `Retry-After` header and JSON `retry_after` value, including fractional seconds, and carries the cooldown into subsequent notifications. If the required wait exceeds the budget, it defers the notification without retrying early. Server errors use exponential backoff (1 then 2 seconds). Permanent HTTP rejections and transport errors are left for the next timer run; transport errors are not immediately retried because delivery may already have occurred.

After updating an existing installation, run `bash SystemdFiles/install-systemd.sh` again (or copy the unit file to `/etc/systemd/system/` and run `systemctl daemon-reload`) to apply the runtime limit.

To run it manually from the repository root: `python3 -m src`

To install development dependencies and run the tests from the repository root:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
```

The tests simulate systemd and Discord responses and use temporary state files; they do not require a systemd host or Discord credentials. CI runs flake8 on the latest Python and tests on Python 3.10.

## Configuration

Settings are read from `.env` in the repository root (python-dotenv searches upward from `src/`). Values in `.env` take precedence over environment variables.

- `DISCORD_TOKEN`: Discord Bot token
- `DISCORD_CHANNEL_ID`: ID of the channel to send notifications to

Optional file, read from the working directory (the systemd unit uses the repository root):

- `ignore_services.json`: a JSON array of service names that are never notified, for example `["foo.service"]`.

The tool creates the following files at runtime:

- `notified_ids.json`: a JSON array of service names already notified as Failed. It is used to avoid duplicate notifications and to detect recovery.
- `notified_ids.json.lock` and `notified_ids.run.lock`: lock files that serialize state updates and overlapping runs. Keep these files in place while the tool is running.
- `logs/`: daily log files. Old files may accumulate.

State updates are written to a temporary file and atomically replaced. If `notified_ids.json` is invalid or is not an array of strings, the tool stops without changing it. Restore a valid copy from backup before retrying; if none is available, inspect and repair the file manually. Resetting it to `[]` loses recovery tracking and can repeat failure notifications.

## Warning / Disclaimer

The developer is not responsible for any problems caused by the user using this project.

## License

The license for this project is [MIT License](LICENSE).
