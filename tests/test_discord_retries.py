import io
from unittest import mock

import pytest
import requests

import src


@pytest.mark.parametrize("headers,body,expected", [
    ({"Retry-After": "1.5"}, None, 1.5),
    ({}, {"retry_after": 0.25, "global": True}, 0.25),
    ({"Retry-After": "1"}, {"retry_after": 2.5}, 2.5),
    ({"Retry-After": "invalid"}, {"retry_after": 0.5}, 0.5),
    ({}, None, 1),
    ({}, [], 1),
    ({"Retry-After": "NaN"}, {"retry_after": -1}, 1),
    ({"Retry-After": "Infinity"}, {"retry_after": "bad"}, 1),
])
def test_rate_limit_waits_before_retry(monkeypatch, clock, response, headers, body, expected):
    post = mock.Mock(side_effect=[response(429, body, headers), response(200)])
    monkeypatch.setattr(src.requests, "post", post)

    src.send_to_discord("token", "channel", "message")

    assert post.call_count == 2
    assert clock == [expected]
    assert all(call.kwargs["timeout"] == (5, 15) for call in post.call_args_list)


@pytest.mark.parametrize("status", [500, 502, 503, 599])
def test_server_error_retries_are_bounded(monkeypatch, clock, response, status):
    post = mock.Mock(side_effect=lambda *args, **kwargs: response(status))
    monkeypatch.setattr(src.requests, "post", post)

    with pytest.raises(requests.HTTPError):
        src.send_to_discord("token", "channel", "message")

    assert post.call_count == 3
    assert clock == [1, 2]


def test_server_error_can_recover(monkeypatch, clock, response):
    post = mock.Mock(side_effect=[response(503), response(200)])
    monkeypatch.setattr(src.requests, "post", post)

    src.send_to_discord("token", "channel", "message")

    assert post.call_count == 2
    assert clock == [1]


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_permanent_rejection_is_not_retried(monkeypatch, clock, response, status):
    post = mock.Mock(return_value=response(status))
    monkeypatch.setattr(src.requests, "post", post)

    with pytest.raises(requests.HTTPError):
        src.send_to_discord("token", "channel", "message")

    assert post.call_count == 1
    assert clock == []


def test_rate_limit_attempts_and_shared_cooldown(monkeypatch, clock, response):
    post = mock.Mock(side_effect=[
        response(429, {"retry_after": 0.5}),
        response(429, {"retry_after": 0.5}),
        response(429, {"retry_after": 0.5}),
        response(200),
    ])
    monkeypatch.setattr(src.requests, "post", post)

    with pytest.raises(requests.HTTPError):
        src.send_to_discord("token", "channel", "first")
    assert post.call_count == 3
    assert clock == [0.5, 0.5]

    src.send_to_discord("token", "channel", "second")

    assert post.call_count == 4
    assert clock == [0.5, 0.5, 0.5]


@pytest.mark.parametrize("delays,expected_calls,expected_sleeps", [
    ([31], 1, []),
    ([20, 20], 2, [20]),
])
def test_rate_limit_wait_budget_does_not_retry_early(monkeypatch, clock, response, delays, expected_calls, expected_sleeps):
    post = mock.Mock(side_effect=[response(429, {"retry_after": delay}) for delay in delays])
    monkeypatch.setattr(src.requests, "post", post)

    with pytest.raises(requests.HTTPError):
        src.send_to_discord("token", "channel", "first")

    assert post.call_count == expected_calls
    assert clock == expected_sleeps
    if delays == [31]:
        with pytest.raises(requests.exceptions.RetryError):
            src.send_to_discord("token", "channel", "second")
        assert post.call_count == 1
        assert clock == []


def test_attachment_is_rewound_for_retry(monkeypatch, clock, response):
    attachment = io.BytesIO(b"journal")
    contents = []

    def post(*args, **kwargs):
        contents.append(kwargs["files"]["file"][1].read())
        return response(503 if len(contents) == 1 else 200)

    monkeypatch.setattr(src.requests, "post", post)

    src.send_to_discord("token", "channel", "message", files={"file": ("journal.txt", attachment)})

    assert contents == [b"journal", b"journal"]


def test_nonseekable_attachment_is_not_resent(monkeypatch, clock, response):
    attachment = mock.Mock(spec=["read"])
    post = mock.Mock(return_value=response(503))
    monkeypatch.setattr(src.requests, "post", post)

    with pytest.raises(requests.exceptions.RetryError):
        src.send_to_discord("token", "channel", "message", files={"file": attachment})

    assert post.call_count == 1
