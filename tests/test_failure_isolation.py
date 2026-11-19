import json
import runpy
import subprocess
import sys
from unittest import mock

import pytest
import requests

import src


FAILED_UNITS = "first.service loaded failed failed First\nsecond.service loaded failed failed Second\n"


@pytest.mark.parametrize("failure", ["journal", "http400", "http429", "http503", "timeout"])
def test_failed_service_does_not_starve_later_failures_or_recoveries(application, monkeypatch, response, caplog, failure):
    src.save_notified_ids(["recovered.service"])
    journals = []
    sent = []

    def check_output(command, **kwargs):
        if isinstance(command, str):
            return FAILED_UNITS
        journals.append(command[2])
        if failure == "journal" and command[2] == "first.service":
            raise subprocess.CalledProcessError(1, command)
        return "journal output"

    def post(*args, **kwargs):
        service = kwargs["json"]["embeds"][0]["title"]
        sent.append(service)
        if service == "first.service":
            if failure == "timeout":
                raise requests.ReadTimeout("test-token test-channel")
            if failure == "http429":
                return response(429, {"retry_after": 0.5})
            return response(400 if failure == "http400" else 503)
        return response(200)

    monkeypatch.setattr(application.subprocess, "check_output", check_output)
    monkeypatch.setattr(src.requests, "post", post)

    assert application.main() == 1
    assert journals == ["first.service", "second.service"]
    assert sent[-2:] == ["second.service", "recovered.service"]
    assert src.load_notified_ids() == ["second.service"]
    assert "1 service notification(s) remain unsuccessful." in caplog.text
    assert "test-token" not in caplog.text
    assert "test-channel" not in caplog.text


def test_recovery_failure_keeps_pending_state_and_continues(application, monkeypatch, response, caplog):
    src.save_notified_ids(["first.service", "second.service"])
    monkeypatch.setattr(application.subprocess, "check_output", lambda *args, **kwargs: "")
    post = mock.Mock(side_effect=[response(403), response(200)])
    monkeypatch.setattr(src.requests, "post", post)

    assert application.main() == 1
    assert post.call_count == 2
    assert src.load_notified_ids() == ["first.service"]
    assert "Recovery notification for first.service remains pending" in caplog.text


def test_successful_retries_update_state_and_exit_successfully(application, monkeypatch, response):
    src.save_notified_ids(["recovered.service"])
    check_output = mock.Mock(side_effect=[FAILED_UNITS, "first journal", "second journal"])
    monkeypatch.setattr(application.subprocess, "check_output", check_output)
    post = mock.Mock(side_effect=[response(429, {"retry_after": 0.25}), response(200), response(503), response(200), response(200)])
    monkeypatch.setattr(src.requests, "post", post)

    assert application.main() == 0
    assert src.load_notified_ids() == ["first.service", "second.service"]


def test_multiple_failures_are_aggregated(application, monkeypatch, response, caplog):
    src.save_notified_ids(["recovered.service"])
    monkeypatch.setattr(application.subprocess, "check_output", mock.Mock(side_effect=[FAILED_UNITS, "journal", "journal"]))
    monkeypatch.setattr(src.requests, "post", mock.Mock(return_value=response(400)))

    assert application.main() == 1
    assert src.load_notified_ids() == ["recovered.service"]
    assert "3 service notification(s) remain unsuccessful." in caplog.text


def test_ignored_and_already_notified_services_remain_failed(application, monkeypatch):
    src.save_notified_ids(["second.service"])
    with open("ignore_services.json", "w") as stream:
        json.dump(["first.service"], stream)
    check_output = mock.Mock(return_value=FAILED_UNITS)
    monkeypatch.setattr(application.subprocess, "check_output", check_output)
    post = mock.Mock()
    monkeypatch.setattr(src.requests, "post", post)

    assert application.main() == 0
    check_output.assert_called_once()
    post.assert_not_called()
    assert src.load_notified_ids() == ["second.service"]


def test_state_write_failure_does_not_starve_later_services(application, monkeypatch, response):
    monkeypatch.setattr(application.subprocess, "check_output", mock.Mock(side_effect=[FAILED_UNITS, "journal", "journal"]))
    monkeypatch.setattr(src.requests, "post", mock.Mock(return_value=response(200)))
    save = src.add_notified_id

    def add_notified_id(service):
        if service == "first.service":
            raise OSError("read-only state")
        save(service)

    monkeypatch.setattr(application, "add_notified_id", add_notified_id)

    assert application.main() == 1
    assert src.load_notified_ids() == ["second.service"]


@pytest.mark.parametrize("unsuccessful", [False, True])
def test_module_entrypoint_returns_batch_exit_code(application, monkeypatch, response, unsuccessful):
    monkeypatch.delitem(sys.modules, "src.__main__")
    monkeypatch.setattr(application.subprocess, "check_output", mock.Mock(side_effect=[FAILED_UNITS, "journal", "journal"]))
    monkeypatch.setattr(src.requests, "post", mock.Mock(return_value=response(400 if unsuccessful else 200)))

    with pytest.raises(SystemExit) as result:
        runpy.run_module("src", run_name="__main__")

    assert result.value.code == (1 if unsuccessful else 0)
