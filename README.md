# report-failed-services

Notifies Discord of services whose status is Failed. It also notifies the services that operated normally after Failed.

## Requirements

- Python 3.6+
- [requirements.txt](requirements.txt): `python-dotenv`, `requests`

## Installation

1. Clone from GitHub repository: `git clone https://github.com/book000/report-failed-services.git`
2. Install the dependency package from `requirements.txt`: `pip3 install -U -r requirements.txt`
3. Create a configuration file (see Configuration below)
4. Register systemd to run report-failed-services periodically: `chmod 777 SystemdFiles/install-systemd.sh && SystemdFiles/install-systemd.sh`

(virtual-environment system is also available)

## Configuration

The configuration file is `.env'.

- `DISCORD_TOKEN`: Discord Bot token
- `DISCORD_CHANNEL_ID`: Discord Send to channel ID

## Warning / Disclaimer

The developer is not responsible for any problems caused by the user using this project.

## License

The license for this project is [MIT License](LICENSE).
