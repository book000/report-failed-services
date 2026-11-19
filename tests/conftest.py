import importlib
from unittest import mock

import pytest

import src


@pytest.fixture
def clock(monkeypatch):
    now = [100.0]
    sleeps = []

    def sleep(delay):
        sleeps.append(delay)
        now[0] += delay

    monkeypatch.setattr(src.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(src.time, "sleep", sleep)
    monkeypatch.setattr(src, "_discord_rate_limit_until", 0.0)
    return sleeps


@pytest.fixture
def application(monkeypatch, tmp_path, clock):
    monkeypatch.chdir(tmp_path)
    with mock.patch("dotenv.load_dotenv"), mock.patch.dict("os.environ", {
        "DISCORD_TOKEN": "test-token",
        "DISCORD_CHANNEL_ID": "test-channel",
    }):
        return importlib.import_module("src.__main__")


@pytest.fixture
def response():
    def make_response(status, body=None, headers=None):
        import json

        import requests

        result = requests.Response()
        result.status_code = status
        result.headers.update(headers or {})
        result._content = json.dumps(body).encode() if body is not None else b"not JSON"
        return result

    return make_response
