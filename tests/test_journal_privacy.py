import json
from unittest import mock

import pytest

import src
from src.journal import redact_journal


FAILED_UNITS = "first.service loaded failed failed First\nsecond.service loaded failed failed Second\n"


@pytest.mark.parametrize("mode,services,expected", [
    ("omit", {"first.service"}, []),
    ("allowlist", set(), []),
    ("allowlist", {"first.service"}, ["first.service"]),
    ("allowlist", {"first", "*.service", "FIRST.service"}, []),
    ("all", set(), ["first.service", "second.service"]),
])
def test_journal_access_and_payload_follow_policy(application, monkeypatch, response, mode, services, expected):
    monkeypatch.setattr(application.config, "JOURNAL_MODE", mode)
    monkeypatch.setattr(application.config, "JOURNAL_SERVICES", services)
    src.save_notified_ids(["recovered.service"])
    read_services = []

    def check_output(command, **kwargs):
        if isinstance(command, str):
            return FAILED_UNITS
        read_services.append(command[2])
        assert command == ["/usr/bin/journalctl", "-u", command[2], "-n", "10", "-l", "--no-pager"]
        return "ordinary diagnostic\npassword=SYNTHETIC_PRIVATE_VALUE\n"

    monkeypatch.setattr(application.subprocess, "check_output", check_output)
    post = mock.Mock(return_value=response(200))
    monkeypatch.setattr(src.requests, "post", post)

    assert application.main() == 0
    assert read_services == expected
    assert src.load_notified_ids() == ["first.service", "second.service"]
    assert post.call_count == 3
    for call in post.call_args_list:
        payload = call.kwargs["json"]
        embed = payload["embeds"][0]
        assert "SYNTHETIC_PRIVATE_VALUE" not in json.dumps(payload)
        if embed["title"] in expected:
            assert embed["fields"] == [{"name": "journal", "value": "```ordinary diagnostic\n[REDACTED]\n```"}]
        else:
            assert "fields" not in embed


@pytest.mark.parametrize("private_line", [
    "token=SYNTHETIC_PRIVATE_VALUE",
    "password=SYNTHETIC_PRIVATE_VALUE",
    'DB_PASSWORD="SYNTHETIC_PRIVATE_VALUE with spaces"',
    'details: {"access_token": "SYNTHETIC_PRIVATE_VALUE"}',
    "API-Key: SYNTHETIC_PRIVATE_VALUE",
    "API key: SYNTHETIC_PRIVATE_VALUE",
    "client_secret = SYNTHETIC_PRIVATE_VALUE",
    "PWD=SYNTHETIC_PRIVATE_VALUE;Database=example",
    "Authorization: Basic SYNTHETIC_PRIVATE_VALUE",
    "header: Bearer SYNTHETIC_PRIVATE_VALUE",
    "Cookie: session=SYNTHETIC_PRIVATE_VALUE",
    "Set-Cookie: session=SYNTHETIC_PRIVATE_VALUE",
    "ConnectionString: SYNTHETIC_PRIVATE_VALUE",
    "Connection string: SYNTHETIC_PRIVATE_VALUE",
    "postgres://name:SYNTHETIC_PRIVATE_VALUE@db.invalid/example",
])
def test_sensitive_journal_lines_are_removed(private_line):
    assert redact_journal("before\n" + private_line + "\nafter", "different-token") == "before\n[REDACTED]\nafter"


def test_configured_bot_token_is_removed_without_a_known_pattern():
    assert redact_journal("unexpected prefix SYNTHETIC_PRIVATE_VALUE suffix", "SYNTHETIC_PRIVATE_VALUE") == "[REDACTED]"


@pytest.mark.parametrize("text", ["", "ordinary diagnostic", "starting\nfailed\n", "timeout\r\nretrying\r\n"])
def test_ordinary_diagnostics_are_preserved(text):
    assert redact_journal(text, "different-token") == text


def test_redaction_precedes_truncation(application, monkeypatch, response):
    journal = "x" * 980 + "\npassword=" + "SYNTHETIC_PRIVATE_VALUE" * 100
    monkeypatch.setattr(application.subprocess, "check_output", mock.Mock(side_effect=[
        "first.service loaded failed failed First", journal,
    ]))
    post = mock.Mock(return_value=response(200))
    monkeypatch.setattr(src.requests, "post", post)

    assert application.main() == 0
    value = post.call_args.kwargs["json"]["embeds"][0]["fields"][0]["value"]
    assert value == "```" + "x" * 980 + "\n[REDACTED]```"


def test_journal_length_limit_is_preserved(application, monkeypatch, response):
    monkeypatch.setattr(application.subprocess, "check_output", mock.Mock(side_effect=[
        "first.service loaded failed failed First", "x" * 2000,
    ]))
    post = mock.Mock(return_value=response(200))
    monkeypatch.setattr(src.requests, "post", post)
    assert application.main() == 0
    assert post.call_args.kwargs["json"]["embeds"][0]["fields"][0]["value"] == "```" + "x" * 1000 + "```"


def test_default_policy_omits_journal(application, monkeypatch):
    monkeypatch.delenv("JOURNAL_MODE", raising=False)
    monkeypatch.delenv("JOURNAL_SERVICES", raising=False)
    assert application.config.load_journal_policy() == ("omit", frozenset())


@pytest.mark.parametrize("mode", ["omit", "allowlist", "all"])
def test_valid_journal_policy(application, monkeypatch, mode):
    monkeypatch.setenv("JOURNAL_MODE", mode)
    monkeypatch.setenv("JOURNAL_SERVICES", '["first.service", "first.service", "second.service"]')
    assert application.config.load_journal_policy() == (mode, frozenset({"first.service", "second.service"}))


@pytest.mark.parametrize("mode", ["", "ALL", "typo"])
def test_invalid_mode_is_rejected(application, monkeypatch, mode):
    monkeypatch.setenv("JOURNAL_MODE", mode)
    with pytest.raises(ValueError, match="JOURNAL_MODE must be"):
        application.config.load_journal_policy()


@pytest.mark.parametrize("services", ["", "broken", "null", "{}", '"first.service"', "[1]", "[null]", '[""]', '[" "]'])
def test_invalid_service_list_is_rejected_without_echoing_input(application, monkeypatch, services):
    monkeypatch.setenv("JOURNAL_MODE", "allowlist")
    monkeypatch.setenv("JOURNAL_SERVICES", services)
    with pytest.raises(ValueError, match="JOURNAL_SERVICES must be a JSON array") as error:
        application.config.load_journal_policy()
    assert str(error.value) in {
        "JOURNAL_SERVICES must be a JSON array of service names.",
        "JOURNAL_SERVICES must be a JSON array of nonempty service names.",
    }
