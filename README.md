# report-failed-services

Notifies a Discord channel of systemd services in the Failed state. It also sends a recovery notification once a previously notified service is no longer Failed.

## Requirements

- Linux with systemd (`systemctl` and `journalctl`)
- Python 3.6+
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

To run it manually from the repository root: `python3 -m src`

## Configuration

Settings are read from `.env` in the repository root (python-dotenv searches upward from `src/`). Values in `.env` take precedence over environment variables.

- `DISCORD_TOKEN`: Discord Bot token
- `DISCORD_CHANNEL_ID`: ID of the channel to send notifications to

Optional file, read from the working directory (the systemd unit uses the repository root):

- `ignore_services.json`: a JSON array of service names that are never notified, for example `["foo.service"]`.

The tool creates the following files at runtime:

- `notified_ids.json`: a JSON array of service names already notified as Failed. It is used to avoid duplicate notifications and to detect recovery.
- `logs/`: daily log files. Old files may accumulate.

## Warning / Disclaimer

The developer is not responsible for any problems caused by the user using this project.

## License

The license for this project is [MIT License](LICENSE).
