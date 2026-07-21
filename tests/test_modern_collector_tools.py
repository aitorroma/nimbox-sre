import json
import os
import unittest
from unittest.mock import patch

from plugins.nimbox_sre import maintenance, runbooks


class _Response:
    status_code = 200
    text = "{}"

    def raise_for_status(self):
        return None

    def json(self):
        return {"ok": True}


class _Client:
    def __init__(self, calls, **_):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        return _Response()

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        return _Response()

    def put(self, url, **kwargs):
        self.calls.append(("put", url, kwargs))
        return _Response()


class ModernCollectorToolTests(unittest.TestCase):
    def setUp(self):
        self.environment = os.environ.copy()
        os.environ["MONIT_API_URL"] = "https://monit.example"
        os.environ["MONIT_AGENT_API_TOKEN"] = "agent-token"
        os.environ["MONIT_API_TOKEN"] = "maintenance-token"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.environment)

    def test_runbooks_is_available_for_approved_reads(self):
        calls = []
        with patch("plugins.nimbox_sre.httpx.Client", side_effect=lambda **kw: _Client(calls, **kw)):
            result = json.loads(runbooks(action="list_approved"))

        self.assertTrue(result["ok"])
        self.assertEqual(calls[0][0], "get")
        self.assertEqual(calls[0][1], "https://monit.example/api/runbooks")
        self.assertEqual(calls[0][2]["params"], {"status": "approved"})
        self.assertEqual(calls[0][2]["headers"], {"Authorization": "Bearer agent-token"})

    def test_indefinite_maintenance_is_explicit_and_has_no_expiry(self):
        calls = []
        with patch("plugins.nimbox_sre.httpx.Client", side_effect=lambda **kw: _Client(calls, **kw)):
            result = json.loads(maintenance(action="enable", hostname="db-1", indefinite=True, reason="planned work"))

        self.assertTrue(result["ok"])
        method, url, kwargs = calls[0]
        self.assertEqual((method, url), ("post", "https://monit.example/api/maintenance/db-1"))
        self.assertEqual(kwargs["json"], {"enabled": True, "reason": "planned work", "requested_by": "nimbox-sre", "indefinite": True})

    def test_indefinite_maintenance_rejects_expiry_fields(self):
        result = json.loads(maintenance(action="enable", hostname="db-1", indefinite=True, duration_minutes=30, reason="planned work"))
        self.assertFalse(result["ok"])
        self.assertIn("cannot include", result["error"])

    def test_agent_closes_incident_with_final_evidence(self):
        calls = []
        from plugins.nimbox_sre import monit_alerts

        with patch("plugins.nimbox_sre.httpx.Client", side_effect=lambda **kw: _Client(calls, **kw)):
            result = json.loads(monit_alerts(action="close", incident_id="inc-1", message="Servicio comprobado y recuperado."))

        self.assertTrue(result["ok"])
        self.assertEqual(calls[0][0], "post")
        self.assertEqual(calls[0][1], "https://monit.example/api/incidents/inc-1/close")
        self.assertEqual(calls[0][2]["json"], {"message": "Servicio comprobado y recuperado."})

    def test_runbook_update_creates_a_version_instead_of_a_copy(self):
        calls = []
        with patch("plugins.nimbox_sre.httpx.Client", side_effect=lambda **kw: _Client(calls, **kw)):
            result = json.loads(runbooks(action="update_draft", runbook_id="rb-1", description="Mejorado", steps=["comprobar"], allowed_actions=["systemctl status app"]))

        self.assertTrue(result["ok"])
        self.assertEqual(calls[0][0], "put")
        self.assertEqual(calls[0][1], "https://monit.example/api/runbooks/rb-1")


if __name__ == "__main__":
    unittest.main()
