"""NimBox SRE tools exposed to the Hermes agent.

The plugin route is intentional: Hermes discovers plugin-provided toolsets,
whereas files merely copied into ``tools/`` are not exposed unless the core
``toolsets.py`` is also modified.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _result(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _error(service: str, exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return _result({"ok": False, "service": service, "error": "upstream returned an error", "status_code": exc.response.status_code})
    if isinstance(exc, httpx.HTTPError):
        return _result({"ok": False, "service": service, "error": "upstream request failed", "detail": str(exc)})
    return _result({"ok": False, "service": service, "error": "tool request failed", "detail": str(exc)})


def _nightingale_ready() -> bool:
    return bool(os.getenv("NIGHTINGALE_TOKEN"))


def _warpgate_ready() -> bool:
    return bool(os.getenv("WARPGATE_TOKEN"))


def _opensre_ready() -> bool:
    return bool(os.getenv("OPENSRE_URL"))


def _maintenance_ready() -> bool:
    return bool(os.getenv("MONIT_API_TOKEN"))


def _monit_alerts_ready() -> bool:
    """The agent token may be split from the maintenance token in production."""
    return bool(os.getenv("MONIT_AGENT_API_TOKEN") or os.getenv("MONIT_API_TOKEN"))


def monit_alerts(
    action: str,
    incident_id: str | None = None,
    **_: Any,
) -> str:
    """Read Modern Collector incidents generated from Monit reports.

    This is intentionally read-only. Operational changes, ownership and
    comments remain out of the agent's automatic alert-review path.
    """
    base_url = os.getenv("MONIT_API_URL", "https://monit.hiveagilectl.sh").rstrip("/")
    token = os.getenv("MONIT_AGENT_API_TOKEN") or os.getenv("MONIT_API_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    if action == "get" and not incident_id:
        return _result({"ok": False, "service": "monit_alerts", "error": "incident_id is required for get"})

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            if action == "list_active":
                response = client.get(f"{base_url}/api/incidents", headers=headers, params={"active_only": "true"})
            elif action == "list_all":
                response = client.get(f"{base_url}/api/incidents", headers=headers, params={"active_only": "false"})
            elif action == "get":
                response = client.get(f"{base_url}/api/incidents/{incident_id}", headers=headers)
            else:
                return _result({"ok": False, "service": "monit_alerts", "error": f"unknown action: {action}"})
            response.raise_for_status()
        return _result({"ok": True, "service": "monit_alerts", "action": action, "incident_id": incident_id, "data": response.json()})
    except Exception as exc:
        return _error("monit_alerts", exc)


def nightingale(action: str, target_id: str | None = None, **_: Any) -> str:
    """Query monitoring targets, active alerts, and alert rules."""
    base_url = os.getenv("NIGHTINGALE_API_URL", "https://collector.nimbox360.com/api/n9e").rstrip("/")
    endpoints = {
        "list_targets": "/targets",
        # Nightingale serves its SPA HTML at /alert-cur-events; the JSON API
        # backing the active-events view is the explicit /list endpoint.
        "list_alerts": "/alert-cur-events/list",
        "list_alert_rules": "/alert-rules",
    }
    if action == "get_target":
        if not target_id:
            return _result({"ok": False, "service": "nightingale", "error": "target_id is required for get_target"})
        path = f"/targets/{target_id}"
    else:
        path = endpoints.get(action)
    if not path:
        return _result({"ok": False, "service": "nightingale", "error": f"unknown action: {action}"})
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            response = client.get(f"{base_url}{path}", headers={"Authorization": f"Bearer {os.environ['NIGHTINGALE_TOKEN']}"})
            response.raise_for_status()
        try:
            data = response.json()
        except json.JSONDecodeError:
            return _result({"ok": False, "service": "nightingale", "error": "upstream returned non-JSON content", "content_type": response.headers.get("content-type", "")})
        return _result({"ok": True, "service": "nightingale", "action": action, "data": data})
    except Exception as exc:
        return _error("nightingale", exc)


def _warpgate_json(response: httpx.Response) -> Any:
    response.raise_for_status()
    return response.json()


def _find_by_name(items: list[dict[str, Any]], name: str, field: str = "name") -> dict[str, Any] | None:
    wanted = name.strip().casefold()
    return next((item for item in items if str(item.get(field, "")).casefold() == wanted), None)


def _ticket_store_path() -> Path:
    state_dir = _state_dir()
    return state_dir / "ticket-secrets.json"


def _state_dir() -> Path:
    """Return the private, persistent state directory owned by Hermes."""
    state_dir = Path(os.getenv("HERMES_HOME", "/opt/data")) / "nimbox-sre"
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    state_dir.chmod(stat.S_IRWXU)
    return state_dir


def _agent_key_paths() -> tuple[Path, Path]:
    private_key = _state_dir() / "agent_ed25519"
    return private_key, private_key.with_suffix(".pub")


def _ensure_agent_ssh_key() -> tuple[str, bool]:
    """Create the agent key once and return its public half and creation state."""
    private_key, public_key = _agent_key_paths()
    created = False
    if not private_key.exists():
        subprocess.run(
            [
                "ssh-keygen", "-q", "-t", "ed25519", "-N", "",
                "-C", "nimbox-sre-agent@hermes", "-f", str(private_key),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        created = True
    private_key.chmod(stat.S_IRUSR | stat.S_IWUSR)
    if not public_key.exists():
        public_key.write_text(subprocess.run(
            ["ssh-keygen", "-y", "-f", str(private_key)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout)
    public_key.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    return public_key.read_text().strip(), created


def _public_key_material(public_key: str) -> str:
    """Normalize an OpenSSH key for comparison without its optional comment.

    Warpgate returns public-key credentials without the comment that was sent
    on creation, so a byte-for-byte comparison would create duplicates.
    """
    return " ".join(public_key.strip().split()[:2])


def _save_ticket_secret(ticket_id: str, secret: str) -> None:
    path = _ticket_store_path()
    try:
        secrets = json.loads(path.read_text()) if path.exists() else {}
    except json.JSONDecodeError:
        secrets = {}
    secrets[ticket_id] = secret
    path.write_text(json.dumps(secrets))
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _load_ticket_secret(ticket_id: str) -> str | None:
    path = _ticket_store_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text()).get(ticket_id)
    except json.JSONDecodeError:
        return None


def _delete_ticket_secret(ticket_id: str) -> None:
    path = _ticket_store_path()
    if not path.exists():
        return
    try:
        secrets = json.loads(path.read_text())
    except json.JSONDecodeError:
        return
    if ticket_id in secrets:
        del secrets[ticket_id]
        path.write_text(json.dumps(secrets))
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _redact(value: str, secret: str) -> str:
    return value.replace(secret, "[REDACTED]")


def _run_ticket_ssh(ticket_id: str, command: str) -> str:
    secret = _load_ticket_secret(ticket_id)
    if not secret:
        return _result({"ok": False, "service": "warpgate", "error": "ticket secret is unavailable; create a new ticket through this agent"})

    host = os.getenv("WARPGATE_SSH_HOST", "geo.nimbox360.com")
    port = os.getenv("WARPGATE_SSH_PORT", "22")
    known_hosts = _ticket_store_path().with_name("known_hosts")
    with tempfile.NamedTemporaryFile("w", delete=False) as askpass:
        askpass.write("#!/bin/sh\nprintf '%s\\n' ticket\n")
        askpass_path = askpass.name
    os.chmod(askpass_path, 0o700)
    try:
        env = os.environ | {"DISPLAY": "nimbox-sre", "SSH_ASKPASS": askpass_path, "SSH_ASKPASS_REQUIRE": "force"}
        completed = subprocess.run(
            [
                "ssh", "-p", port,
                "-o", "ConnectTimeout=15",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", f"UserKnownHostsFile={known_hosts}",
                "-o", "PreferredAuthentications=password",
                "-o", "PubkeyAuthentication=no",
                "-o", "NumberOfPasswordPrompts=1",
                f"ticket-{secret}@{host}",
                command,
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = _redact((completed.stdout + completed.stderr).strip(), secret)
        return _result({"ok": completed.returncode == 0, "service": "warpgate", "action": "run_ssh_command", "ticket_id": ticket_id, "exit_code": completed.returncode, "output": output[-8000:]})
    except subprocess.TimeoutExpired:
        return _result({"ok": False, "service": "warpgate", "error": "SSH connection timed out", "ticket_id": ticket_id})
    finally:
        Path(askpass_path).unlink(missing_ok=True)


def _run_agent_ssh(username: str, target_name: str, command: str) -> str:
    """Run a command with Hermes' private key through a named Warpgate target."""
    private_key, _ = _agent_key_paths()
    if not private_key.exists():
        return _result({"ok": False, "service": "warpgate", "error": "agent SSH key is unavailable; run provision_agent_ssh_key first"})
    host = os.getenv("WARPGATE_SSH_HOST", "geo.nimbox360.com")
    port = os.getenv("WARPGATE_SSH_PORT", "22")
    known_hosts = _ticket_store_path().with_name("known_hosts")
    try:
        completed = subprocess.run(
            [
                "ssh", "-p", port,
                "-i", str(private_key),
                "-o", "BatchMode=yes",
                "-o", "IdentitiesOnly=yes",
                "-o", "ConnectTimeout=15",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", f"UserKnownHostsFile={known_hosts}",
                f"{username}:{target_name}@{host}",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = (completed.stdout + completed.stderr).strip()
        result: dict[str, Any] = {
            "ok": completed.returncode == 0,
            "service": "warpgate",
            "action": "run_agent_ssh_command",
            "target_name": target_name,
            "exit_code": completed.returncode,
            "output": output[-8000:],
        }
        if completed.returncode != 0 and not output:
            result["error"] = "Warpgate accepted the agent key but the upstream target closed the SSH channel; install Warpgate's client public key in the remote user's authorized_keys"
        return _result(result)
    except subprocess.TimeoutExpired:
        return _result({"ok": False, "service": "warpgate", "error": "SSH connection timed out", "target_name": target_name})


def warpgate(
    action: str,
    username: str = "agente",
    user_id: str | None = None,
    target_id: str | None = None,
    target_name: str | None = None,
    ticket_id: str | None = None,
    command: str | None = None,
    duration: int = 3600,
    number_of_uses: int | None = None,
    description: str = "",
    host: str | None = None,
    port: int = 22,
    ssh_username: str = "root",
    role_name: str = "agentes",
    key_label: str = "nimbox-sre-hermes",
    **_: Any,
) -> str:
    """Manage agent SSH access through Warpgate's admin API.

    The configured WARPGATE_TOKEN is an administrator token. Tickets are
    deliberately issued to the constrained ``agente`` account by default,
    never to the administrator account.
    """
    base_url = os.getenv("WARPGATE_API_URL", "https://geo.nimbox360.com/@warpgate/admin/api").rstrip("/")
    headers = {"X-Warpgate-Token": os.environ["WARPGATE_TOKEN"]}
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            if action == "list_targets":
                response = client.get(f"{base_url}/targets", headers=headers)
            elif action == "list_users":
                response = client.get(f"{base_url}/users", headers=headers)
            elif action == "list_tickets":
                response = client.get(f"{base_url}/tickets", headers=headers)
            elif action == "get_ssh_client_keys":
                response = client.get(f"{base_url}/ssh/own-keys", headers=headers)
            elif action == "provision_agent_ssh_key":
                users = _warpgate_json(client.get(f"{base_url}/users", headers=headers))
                user = _find_by_name(users, username, "username")
                if not user:
                    return _result({"ok": False, "service": "warpgate", "error": f"user not found: {username}"})
                public_key, key_created = _ensure_agent_ssh_key()
                credentials = _warpgate_json(client.get(
                    f"{base_url}/users/{user['id']}/credentials/public-keys", headers=headers,
                ))
                key_material = _public_key_material(public_key)
                existing = next((
                    item for item in credentials
                    if _public_key_material(str(item.get("openssh_public_key", ""))) == key_material
                ), None)
                if existing:
                    return _result({
                        "ok": True,
                        "service": "warpgate",
                        "action": action,
                        "data": {
                            "username": user["username"],
                            "credential_id": existing.get("id"),
                            "label": existing.get("label"),
                            "key_created": key_created,
                            "credential_already_exists": True,
                            "private_key_stored": True,
                        },
                    })
                credential = _warpgate_json(client.post(
                    f"{base_url}/users/{user['id']}/credentials/public-keys",
                    headers=headers,
                    json={"label": key_label, "openssh_public_key": public_key},
                ))
                return _result({
                    "ok": True,
                    "service": "warpgate",
                    "action": action,
                    "data": {
                        "username": user["username"],
                        "credential_id": credential.get("id"),
                        "label": credential.get("label", key_label),
                        "key_created": key_created,
                        "credential_already_exists": False,
                        "private_key_stored": True,
                    },
                })
            elif action == "list_ticket_requests":
                response = client.get(f"{base_url}/ticket-requests", headers=headers)
            elif action == "create_ticket":
                if not user_id:
                    users = _warpgate_json(client.get(f"{base_url}/users", headers=headers))
                    user = _find_by_name(users, username, "username")
                    if not user:
                        return _result({"ok": False, "service": "warpgate", "error": f"user not found: {username}"})
                    user_id = user["id"]
                if not target_id:
                    if not target_name:
                        return _result({"ok": False, "service": "warpgate", "error": "target_name or target_id is required for create_ticket"})
                    targets = _warpgate_json(client.get(f"{base_url}/targets", headers=headers))
                    target = _find_by_name(targets, target_name)
                    if not target:
                        return _result({"ok": False, "service": "warpgate", "error": f"target not found: {target_name}"})
                    target_id = target["id"]
                    target_name = target["name"]
                if not 60 <= duration <= 86_400:
                    return _result({"ok": False, "service": "warpgate", "error": "duration must be between 60 and 86400 seconds"})
                if number_of_uses is not None and not 1 <= number_of_uses <= 100:
                    return _result({"ok": False, "service": "warpgate", "error": "number_of_uses must be between 1 and 100, or omitted for unlimited uses"})
                expiry = (datetime.now(UTC) + timedelta(seconds=duration)).isoformat().replace("+00:00", "Z")
                ticket_request = {
                    "username": username,
                    "user_id": user_id,
                    "target_id": target_id,
                    "target_name": target_name or "",
                    "expiry": expiry,
                    "description": description,
                }
                if number_of_uses is not None:
                    ticket_request["number_of_uses"] = number_of_uses
                response = client.post(f"{base_url}/tickets", headers=headers, json=ticket_request)
                ticket_and_secret = _warpgate_json(response)
                ticket = ticket_and_secret["ticket"]
                _save_ticket_secret(ticket["id"], ticket_and_secret["secret"])
                return _result({"ok": True, "service": "warpgate", "action": action, "data": {"ticket": ticket, "secret_stored": True}})
            elif action == "run_ssh_command":
                if not ticket_id or not command:
                    return _result({"ok": False, "service": "warpgate", "error": "ticket_id and command are required for run_ssh_command"})
                return _run_ticket_ssh(ticket_id, command)
            elif action == "run_agent_ssh_command":
                if not target_name or not command:
                    return _result({"ok": False, "service": "warpgate", "error": "target_name and command are required for run_agent_ssh_command"})
                return _run_agent_ssh(username, target_name, command)
            elif action == "revoke_ticket":
                if not ticket_id:
                    return _result({"ok": False, "service": "warpgate", "error": "ticket_id is required for revoke_ticket"})
                response = client.delete(f"{base_url}/tickets/{ticket_id}", headers=headers)
                response.raise_for_status()
                _delete_ticket_secret(ticket_id)
                return _result({"ok": True, "service": "warpgate", "action": action, "ticket_id": ticket_id, "access_revoked": True})
            elif action == "create_ssh_target":
                if not host or not target_name:
                    return _result({"ok": False, "service": "warpgate", "error": "target_name and host are required for create_ssh_target"})
                if not 1 <= port <= 65535:
                    return _result({"ok": False, "service": "warpgate", "error": "port must be between 1 and 65535"})
                target = _warpgate_json(client.post(f"{base_url}/targets", headers=headers, json={
                    "name": target_name,
                    "description": description or host,
                    "options": {"kind": "Ssh", "host": host, "port": port, "username": ssh_username, "auth": {"kind": "PublicKey"}},
                }))
                roles = _warpgate_json(client.get(f"{base_url}/roles", headers=headers))
                role = _find_by_name(roles, role_name)
                if not role:
                    return _result({"ok": False, "service": "warpgate", "error": f"target was created but role not found: {role_name}", "target": target})
                assignment = client.post(f"{base_url}/targets/{target['id']}/roles/{role['id']}", headers=headers, json={})
                assignment.raise_for_status()
                return _result({"ok": True, "service": "warpgate", "action": action, "data": {"target": target, "role": role_name}})
            else:
                return _result({"ok": False, "service": "warpgate", "error": f"unknown action: {action}"})
            response.raise_for_status()
        return _result({"ok": True, "service": "warpgate", "action": action, "data": response.json()})
    except Exception as exc:
        return _error("warpgate", exc)


def opensre(action: str, alert: str | None = None, **_: Any) -> str:
    """Check OpenSRE health or request an incident investigation."""
    base_url = os.environ["OPENSRE_URL"].rstrip("/")
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            if action == "health":
                response = client.get(f"{base_url}/health")
            elif action == "investigate":
                if not alert:
                    return _result({"ok": False, "service": "opensre", "error": "alert is required for investigate"})
                response = client.post(f"{base_url}/investigate", json={"alert": alert})
            else:
                return _result({"ok": False, "service": "opensre", "error": f"unknown action: {action}"})
            response.raise_for_status()
        return _result({"ok": True, "service": "opensre", "action": action, "data": response.json()})
    except Exception as exc:
        return _error("opensre", exc)


def maintenance(
    action: str,
    hostname: str | None = None,
    duration_minutes: int | None = None,
    duration_seconds: int | None = None,
    until: str | None = None,
    reason: str = "",
    requested_by: str = "nimbox-sre",
    **_: Any,
) -> str:
    """Read or manage maintenance windows in Modern Collector.

    Maintenance is time-bounded by design: an enabled window needs an explicit
    duration or expiry so a host cannot be muted indefinitely by accident.
    """
    base_url = os.getenv("MONIT_API_URL", "https://monit.hiveagilectl.sh").rstrip("/")
    headers = {"Authorization": f"Bearer {os.environ['MONIT_API_TOKEN']}"}
    if action in {"get", "enable", "disable"} and not hostname:
        return _result({"ok": False, "service": "maintenance", "error": f"hostname is required for {action}"})
    if action == "enable":
        expiry_fields = sum(value is not None for value in (duration_minutes, duration_seconds, until))
        if expiry_fields != 1:
            return _result({"ok": False, "service": "maintenance", "error": "enable requires exactly one of duration_minutes, duration_seconds, or until"})
        if duration_minutes is not None and not 1 <= duration_minutes <= 10_080:
            return _result({"ok": False, "service": "maintenance", "error": "duration_minutes must be between 1 and 10080"})
        if duration_seconds is not None and not 60 <= duration_seconds <= 604_800:
            return _result({"ok": False, "service": "maintenance", "error": "duration_seconds must be between 60 and 604800"})
        if not reason.strip():
            return _result({"ok": False, "service": "maintenance", "error": "reason is required to enable maintenance"})
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            if action == "list":
                response = client.get(f"{base_url}/api/maintenance", headers=headers)
            elif action == "get":
                response = client.get(f"{base_url}/api/maintenance/{hostname}", headers=headers)
            elif action == "enable":
                payload: dict[str, Any] = {"enabled": True, "reason": reason, "requested_by": requested_by}
                if duration_minutes is not None:
                    payload["duration_minutes"] = duration_minutes
                elif duration_seconds is not None:
                    payload["duration_seconds"] = duration_seconds
                else:
                    payload["until"] = until
                response = client.post(
                    f"{base_url}/api/maintenance/{hostname}", headers=headers,
                    json=payload,
                )
            elif action == "disable":
                response = client.delete(f"{base_url}/api/maintenance/{hostname}", headers=headers)
            else:
                return _result({"ok": False, "service": "maintenance", "error": f"unknown action: {action}"})
            response.raise_for_status()
        try:
            data: Any = response.json()
        except json.JSONDecodeError:
            data = {"status_code": response.status_code, "body": response.text[:1000]}
        return _result({"ok": True, "service": "maintenance", "action": action, "hostname": hostname, "data": data})
    except Exception as exc:
        return _error("maintenance", exc)


_ACTION_PROPERTY = {
    "type": "string",
    "description": "Operation to execute.",
}

NIGHTINGALE_SCHEMA = {
    "name": "nightingale",
    "description": "Consulta Nightingale para ver hosts monitorizados, alertas activas, reglas y el detalle de un host.",
    "parameters": {"type": "object", "properties": {"action": {**_ACTION_PROPERTY, "enum": ["list_targets", "get_target", "list_alerts", "list_alert_rules"]}, "target_id": {"type": "string", "description": "ID del host, obligatorio para get_target."}}, "required": ["action"]},
}
WARPGATE_SCHEMA = {
    "name": "warpgate",
    "description": "Gestiona acceso SSH con la API admin de Warpgate. `run_agent_ssh_command` usa la clave privada persistente de Hermes con el usuario restringido agente. Los tickets se emiten por defecto para ese mismo usuario y, sin number_of_uses, pueden reutilizarse hasta expirar.",
    "parameters": {"type": "object", "properties": {"action": {**_ACTION_PROPERTY, "enum": ["list_targets", "list_users", "list_tickets", "list_ticket_requests", "get_ssh_client_keys", "provision_agent_ssh_key", "create_ticket", "run_ssh_command", "run_agent_ssh_command", "revoke_ticket", "create_ssh_target"]}, "username": {"type": "string", "default": "agente", "description": "Usuario receptor del ticket o de la clave; usa agente salvo instrucción explícita."}, "user_id": {"type": "string"}, "target_id": {"type": "string"}, "target_name": {"type": "string", "description": "Nombre del destino existente; obligatorio para run_agent_ssh_command."}, "ticket_id": {"type": "string", "description": "ID de un ticket creado por esta herramienta; requerido para run_ssh_command y revoke_ticket."}, "command": {"type": "string", "description": "Comando remoto no interactivo; requerido para las acciones de ejecución SSH."}, "duration": {"type": "integer", "minimum": 60, "maximum": 86400, "default": 3600}, "number_of_uses": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Omitir para usos ilimitados durante la vigencia del ticket."}, "description": {"type": "string"}, "host": {"type": "string", "description": "IP o hostname SSH; obligatorio al crear un host."}, "port": {"type": "integer", "minimum": 1, "maximum": 65535, "default": 22}, "ssh_username": {"type": "string", "default": "root"}, "role_name": {"type": "string", "default": "agentes"}, "key_label": {"type": "string", "default": "nimbox-sre-hermes", "description": "Etiqueta de la credencial creada en Warpgate."}}, "required": ["action"]},
}
OPENSRE_SCHEMA = {
    "name": "opensre",
    "description": "Consulta la salud de OpenSRE o solicita una investigación de causa raíz para una alerta.",
    "parameters": {"type": "object", "properties": {"action": {**_ACTION_PROPERTY, "enum": ["health", "investigate"]}, "alert": {"type": "string", "description": "Descripción completa de la alerta, obligatoria para investigate."}}, "required": ["action"]},
}
MAINTENANCE_SCHEMA = {
    "name": "maintenance",
    "description": "Consulta ventanas de mantenimiento del Modern Collector. Activar o desactivar mantenimiento cambia el estado operativo y requiere confirmación explícita del usuario.",
    "parameters": {"type": "object", "properties": {"action": {**_ACTION_PROPERTY, "enum": ["list", "get", "enable", "disable"]}, "hostname": {"type": "string", "description": "Host requerido para get, enable y disable."}, "duration_minutes": {"type": "integer", "minimum": 1, "maximum": 10080, "description": "Duración acotada de mantenimiento; usar exactamente una forma de expiración."}, "duration_seconds": {"type": "integer", "minimum": 60, "maximum": 604800, "description": "Alternativa de duración en segundos."}, "until": {"type": "string", "description": "Alternativa de expiración ISO-8601 con zona horaria."}, "reason": {"type": "string", "description": "Motivo obligatorio al activar mantenimiento."}, "requested_by": {"type": "string", "default": "nimbox-sre", "description": "Identidad registrada por Modern Collector."}}, "required": ["action"]},
}
MONIT_ALERTS_SCHEMA = {
    "name": "monit_alerts",
    "description": "Consulta las incidencias y alertas generadas por Modern Collector a partir de Monit. Para una petición de alertas activas, úsala junto con nightingale(list_alerts). Es de solo lectura.",
    "parameters": {"type": "object", "properties": {"action": {**_ACTION_PROPERTY, "enum": ["list_active", "list_all", "get"]}, "incident_id": {"type": "string", "description": "ID de incidente de Modern Collector; obligatorio para get."}}, "required": ["action"]},
}


def register(ctx: Any) -> None:
    """Register the NimBox integrations in a plugin-owned toolset."""
    ctx.register_tool(name="nightingale", toolset="nimbox_sre", schema=NIGHTINGALE_SCHEMA, handler=lambda args, **kw: nightingale(**args, **kw), check_fn=_nightingale_ready, requires_env=["NIGHTINGALE_TOKEN"], emoji="📊")
    ctx.register_tool(name="warpgate", toolset="nimbox_sre", schema=WARPGATE_SCHEMA, handler=lambda args, **kw: warpgate(**args, **kw), check_fn=_warpgate_ready, requires_env=["WARPGATE_TOKEN"], emoji="🔐")
    ctx.register_tool(name="opensre", toolset="nimbox_sre", schema=OPENSRE_SCHEMA, handler=lambda args, **kw: opensre(**args, **kw), check_fn=_opensre_ready, requires_env=["OPENSRE_URL"], emoji="🩺")
    ctx.register_tool(name="maintenance", toolset="nimbox_sre", schema=MAINTENANCE_SCHEMA, handler=lambda args, **kw: maintenance(**args, **kw), check_fn=_maintenance_ready, requires_env=["MONIT_API_TOKEN"], emoji="🛠️")
    ctx.register_tool(name="monit_alerts", toolset="nimbox_sre", schema=MONIT_ALERTS_SCHEMA, handler=lambda args, **kw: monit_alerts(**args, **kw), check_fn=_monit_alerts_ready, requires_env=["MONIT_AGENT_API_TOKEN|MONIT_API_TOKEN"], emoji="🚨")
