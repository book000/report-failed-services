import unittest
from unittest import mock

import requests

from src import send_to_discord


class SendToDiscordTimeoutTest(unittest.TestCase):
    @mock.patch("src.requests.post")
    def test_json_branch_passes_timeout(self, post):
        post.return_value.status_code = 200
        send_to_discord("token", "1", "message")

        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["timeout"], (5, 15))

    @mock.patch("src.requests.post")
    def test_files_branch_passes_timeout(self, post):
        post.return_value.status_code = 200
        send_to_discord("token", "1", "message", files={"file": b"x"})

        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["timeout"], (5, 15))

    @mock.patch("src.requests.post")
    def test_timeout_exception_propagates(self, post):
        post.side_effect = requests.exceptions.ReadTimeout("read timed out")

        with self.assertRaises(requests.exceptions.ReadTimeout) as ctx:
            send_to_discord("token", "1", "message")

        self.assertEqual(str(ctx.exception), "read timed out")


if __name__ == "__main__":
    unittest.main()
