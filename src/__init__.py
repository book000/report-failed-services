import datetime
import fcntl
import json
import logging
import math
import os
import time
import tempfile
from contextlib import contextmanager
from logging.handlers import TimedRotatingFileHandler
import requests


def init_logger(child_name: str = None) -> logging.Logger:
    _logger = logging.getLogger("report-failed-services")
    if child_name is not None:
        _logger = _logger.getChild(child_name)
    dt = datetime.datetime.now().date()
    date_time = dt.strftime("%Y-%m-%d")

    if not os.path.exists("logs/"):
        os.mkdir("logs/")

    rotatedHandler = TimedRotatingFileHandler(
        filename="logs/%s.log" % date_time,
        encoding="UTF-8",
        when="MIDNIGHT",
        backupCount=30
    )
    rotatedHandler.setLevel(logging.INFO)
    rotatedHandler.setFormatter(logging.Formatter('[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s'))
    _logger.addHandler(rotatedHandler)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(logging.Formatter('[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s'))
    _logger.addHandler(streamHandler)

    return _logger


logger = init_logger()

DISCORD_TIMEOUT = (5, 15)  # (connect, read) seconds
DISCORD_MAX_ATTEMPTS = 3
DISCORD_MAX_RETRY_WAIT = 30
_discord_rate_limit_until = 0.0


def _rate_limit_delay(response, fallback):
    values = [response.headers.get("Retry-After")]
    try:
        body = response.json()
        if isinstance(body, dict):
            values.append(body.get("retry_after"))
    except ValueError:
        pass
    delays = []
    for value in values:
        try:
            delay = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(delay) and delay >= 0:
            delays.append(delay)
    return max(delays) if delays else fallback


def send_to_discord(token, channelId, message, embed=None, files=None):
    global _discord_rate_limit_until
    headers = {
        "Authorization": "Bot {token}".format(token=token),
        "User-Agent": "Bot"
    }
    payload = {"content": message, "embeds": [embed] if embed is not None else []}
    url = "https://discord.com/api/channels/{channelId}/messages".format(channelId=channelId)
    file_positions = []
    if files:
        values = files.values() if isinstance(files, dict) else (value for name, value in files)
        for value in values:
            stream = value[1] if isinstance(value, tuple) else value
            if hasattr(stream, "read"):
                try:
                    position = stream.tell()
                except (AttributeError, OSError):
                    position = None
                file_positions.append((stream, position))

    waited = 0.0
    for attempt in range(DISCORD_MAX_ATTEMPTS):
        delay = max(0.0, _discord_rate_limit_until - time.monotonic())
        if delay > DISCORD_MAX_RETRY_WAIT - waited:
            raise requests.exceptions.RetryError("Discord rate-limit wait exceeds the retry budget.")
        if delay:
            time.sleep(delay)
            waited += delay
        if attempt:
            for stream, position in file_positions:
                if position is None:
                    raise requests.exceptions.RetryError("Cannot retry a non-seekable Discord attachment.")
                stream.seek(position)
        if files:
            response = requests.post(url, headers=headers, data={"payload_json": json.dumps(payload)}, files=files, timeout=DISCORD_TIMEOUT)
        else:
            response = requests.post(url, headers=headers, json=payload, timeout=DISCORD_TIMEOUT)
        if response.status_code == 429:
            delay = _rate_limit_delay(response, 2 ** attempt)
            _discord_rate_limit_until = time.monotonic() + delay
        elif 500 <= response.status_code < 600:
            delay = 2 ** attempt
        else:
            response.raise_for_status()
            return
        if attempt == DISCORD_MAX_ATTEMPTS - 1 or delay > DISCORD_MAX_RETRY_WAIT - waited:
            response.raise_for_status()
        if response.status_code != 429:
            time.sleep(delay)
            waited += delay


@contextmanager
def state_lock(path="notified_ids.json.lock"):
    with open(path, "a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def _load_notified_ids():
    try:
        with open("notified_ids.json", "r", encoding="utf-8") as f:
            notified_ids = json.load(f)
    except FileNotFoundError:
        return []
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("Invalid notified_ids.json; restore a valid state file before retrying.") from error
    if not isinstance(notified_ids, list) or not all(isinstance(item, str) for item in notified_ids):
        raise ValueError("Invalid notified_ids.json; restore a valid state file before retrying.")
    return notified_ids


def load_notified_ids() -> list:
    with state_lock():
        return _load_notified_ids()


def _save_notified_ids(notified_ids):
    if not isinstance(notified_ids, list) or not all(isinstance(item, str) for item in notified_ids):
        raise ValueError("Notification state must be a list of service names.")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=".", prefix=".notified_ids.", delete=False) as f:
            temp_path = f.name
            json.dump(notified_ids, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, "notified_ids.json")
    finally:
        if temp_path is not None and os.path.exists(temp_path):
            os.unlink(temp_path)


def add_notified_id(notified_id):
    with state_lock():
        notified_ids = _load_notified_ids()
        if notified_id not in notified_ids:
            notified_ids.append(notified_id)
            _save_notified_ids(notified_ids)


def remove_notified_id(notified_id):
    with state_lock():
        notified_ids = _load_notified_ids()
        if notified_id in notified_ids:
            notified_ids.remove(notified_id)
            _save_notified_ids(notified_ids)


def save_notified_ids(notified_ids: list):
    with state_lock():
        _save_notified_ids(notified_ids)


def get_ignore_services() -> list:
    logger.debug("load_ignore_services()")
    ignore_services = []
    if os.path.exists("ignore_services.json"):
        with open("ignore_services.json", "r") as f:
            ignore_services = json.load(f)
    return ignore_services
