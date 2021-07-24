import socket
import subprocess
from datetime import datetime, timezone

from src import add_notified_id, config, get_ignore_services, load_notified_ids, remove_notified_id, send_to_discord

if __name__ == "__main__":
    result: str = subprocess.check_output("/usr/bin/systemctl list-units -t service --failed --full --all --no-legend --plain", shell=True, universal_newlines=True)

    result = result.strip()
    while "  " in result:
        result = result.replace("  ", " ")
    rows = result.splitlines()

    ignore_services = get_ignore_services()
    notified_ids = load_notified_ids()
    not_faileds = notified_ids

    for row in rows:
        cols = row.split(" ")
        service_name = cols[0]
        is_loaded = cols[1] == "loaded"
        status = cols[2]
        sub_status = cols[3]
        description = " ".join(cols[4:])

        print("service_name", service_name)

        if service_name in not_faileds:
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

        service_status = subprocess.check_output("/usr/bin/journalctl -u " + service_name + " -n 10 -l --no-pager", shell=True, universal_newlines=True)

        send_to_discord(config.DISCORD_TOKEN, config.DISCORD_CHANNEL_ID, "", {
            "title": service_name,
            "description": description,
            "fields": [
                {
                    "name": "journal",
                    "value": "```" + (service_status if len(service_status) < 1000 else service_status[:1000]) + "```"
                }
            ],
            "author": {
                "name": socket.gethostname()
            },
            "color": 0xff0000,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        add_notified_id(service_name)

    for not_failed in not_faileds:
        print("not_failed", not_failed)
        remove_notified_id(not_failed)
