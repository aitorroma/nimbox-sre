import json
import os
import unittest
from unittest.mock import patch

from plugins.nimbox_sre import monit_alerts


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {"count": 1, "items": [{"id": "service_down|host|nginx"}]}


class _Client:
    def __init__(self, calls, **_):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _Response()


class MonitAlertsTests(unittest.TestCase):
    def test_list_active_uses_modern_collector_incidents_api(self):
        calls = []
        environment = os.environ.copy()
        os.environ["MONIT_API_URL"] = "https://monit.example"
        os.environ["MONIT_AGENT_API_TOKEN"] = "agent-token"
        try:
            with patch("plugins.nimbox_sre.httpx.Client", side_effect=lambda **kw: _Client(calls, **kw)):
                result = json.loads(monit_alerts(action="list_active"))
        finally:
            os.environ.clear()
            os.environ.update(environment)

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["count"], 1)
        self.assertEqual(calls[0][0], "https://monit.example/api/incidents")
        self.assertEqual(calls[0][1]["params"], {"active_only": "true"})
        self.assertEqual(calls[0][1]["headers"], {"Authorization": "Bearer agent-token"})


if __name__ == "__main__":
    unittest.main()
