import socket
import subprocess
import sys
from datetime import datetime, timezone

from src import add_notified_id, config, get_ignore_services, load_notified_ids, logger, remove_notified_id, send_to_discord, state_lock
from src.journal import redact_journal


def main() -> int:
    with state_lock("notified_ids.run.lock"):
        return _run()


def _run() -> int:
    unsuccessful = 0
    result: str = subprocess.check_output("/usr/bin/systemctl list-units -t service --failed --full --all --no-legend --plain", shell=True, universal_newlines=True)

    result = result.strip()
    while "  " in result:
        result = result.replace("  ", " ")
    rows = result.splitlines()

    ignore_services = get_ignore_services()
    notified_ids = load_notified_ids()
    not_faileds = load_notified_ids()

    for row in rows:
        cols = row.split(" ")
        service_name = cols[0].strip()
        is_loaded = cols[1] == "loaded"
        status = cols[2].strip()
        sub_status = cols[3].strip()
        description = " ".join(cols[4:]).strip()

        print("service_name", service_name)

        while service_name in not_faileds:
            not_faileds.remove(service_name)

        if service_name in ignore_services:
            print("-> ignored")
            continue
        if service_name in notified_ids:
            print("-> notified")
            continue

        print("is_loaded", is_loaded)
        print("status", status)
        print("sub_status", sub_status)
        print("description", description)

        try:
            embed = {
                "title": service_name,
                "description": "`" + description + "`",
                "footer": {
                    "text": socket.gethostname()
                },
                "color": 0xff0000,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if config.JOURNAL_MODE == "all" or (config.JOURNAL_MODE == "allowlist" and service_name in config.JOURNAL_SERVICES):
                service_status = subprocess.check_output(
                    ["/usr/bin/journalctl", "-u", service_name, "-n", "10", "-l", "--no-pager"],
                    universal_newlines=True)
                service_status = redact_journal(service_status, config.DISCORD_TOKEN)
                embed["fields"] = [{"name": "journal", "value": "```" + service_status[:1000] + "```"}]

            send_to_discord(config.DISCORD_TOKEN, config.DISCORD_CHANNEL_ID, "", embed)
            add_notified_id(service_name)

        except Exception as error:
            unsuccessful += 1
            logger.error("Failure notification for %s remains pending (%s).", service_name, type(error).__name__)

    for not_failed in not_faileds:
        print("not_failed", not_failed)
        try:
            send_to_discord(config.DISCORD_TOKEN, config.DISCORD_CHANNEL_ID, "", {
                "title": not_failed,
                "footer": {
                    "text": socket.gethostname()
                },
                "color": 0x00ff00,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            remove_notified_id(not_failed)

        except Exception as error:
            unsuccessful += 1
            logger.error("Recovery notification for %s remains pending (%s).", not_failed, type(error).__name__)

    if unsuccessful:
        logger.error("%d service notification(s) remain unsuccessful.", unsuccessful)
    return 1 if unsuccessful else 0


if __name__ == "__main__":
    sys.exit(main())
