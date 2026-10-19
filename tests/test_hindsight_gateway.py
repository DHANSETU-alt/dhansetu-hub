import os
import unittest
from unittest.mock import patch

from orchestrator import hindsight_gateway
from orchestrator import paperclip_gateway


class HindsightGatewayTests(unittest.TestCase):
    def test_unconfigured_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(hindsight_gateway.status(), "not configured (set HINDSIGHT_API_URL)")

    def test_network_failure_is_unavailable(self):
        with patch.dict(os.environ, {"HINDSIGHT_API_URL": "http://127.0.0.1:8888"}), patch(
            "urllib.request.urlopen", side_effect=OSError("offline")
        ):
            self.assertEqual(hindsight_gateway.status(), "unavailable")

    def test_paperclip_unconfigured_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(paperclip_gateway.status(), "not configured (set PAPERCLIP_API_URL)")

    def test_paperclip_network_failure_is_unavailable(self):
        with patch.dict(os.environ, {"PAPERCLIP_API_URL": "http://127.0.0.1:3100"}), patch(
            "urllib.request.urlopen", side_effect=OSError("offline")
        ):
            self.assertEqual(paperclip_gateway.status(), "unavailable")
