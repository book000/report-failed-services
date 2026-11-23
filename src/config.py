from dotenv import load_dotenv
import json
import os
from src import init_logger

logger = init_logger("Config")

load_dotenv(override=True)


def getKey(key: str, default_value=None):
    value = os.getenv(key)
    if default_value is None and value is None:
        logger.critical("{} is not defined.".format(key))
        exit(1)
    return value


DISCORD_TOKEN = getKey("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = getKey("DISCORD_CHANNEL_ID")


def load_journal_policy():
    mode = os.getenv("JOURNAL_MODE", "omit")
    if mode not in {"omit", "allowlist", "all"}:
        raise ValueError("JOURNAL_MODE must be omit, allowlist, or all.")
    try:
        services = json.loads(os.getenv("JOURNAL_SERVICES", "[]"))
    except ValueError:
        raise ValueError("JOURNAL_SERVICES must be a JSON array of service names.") from None
    if not isinstance(services, list) or not all(isinstance(service, str) and service.strip() for service in services):
        raise ValueError("JOURNAL_SERVICES must be a JSON array of nonempty service names.")
    return mode, frozenset(services)


JOURNAL_MODE, JOURNAL_SERVICES = load_journal_policy()
