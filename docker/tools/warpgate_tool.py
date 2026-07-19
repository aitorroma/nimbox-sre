"""Warpgate Tool -- manage server access via Warpgate."""
import json
import os
import logging

logger = logging.getLogger(__name__)

# --- Availability check ---
def check_warpgate_requirements() -> bool:
    """Return True if the tool's dependencies are available."""
    return bool(os.getenv("WARPGATE_TOKEN"))

# --- Handler ---
def warpgate_tool(action: str, **kwargs) -> str:
    """Manage server access via Warpgate."""
    import httpx
    from datetime import datetime, timedelta
    
    token = os.getenv("WARPGATE_TOKEN")
    base_url = os.getenv("WARPGATE_API_URL", "https://geo.nimbox360.com/@warpgate/admin/api")
    
    if not token:
        return json.dumps({"error": "WARPGATE_TOKEN not configured"})
    
    headers = {"X-Warpgate-Token": token}
    
    try:
        with httpx.Client(verify=False) as client:
            if action == "list_targets":
                resp = client.get(f"{base_url}/targets", headers=headers)
                return json.dumps(resp.json())
            
            elif action == "create_ticket":
                user_id = kwargs.get("user_id")
                target_id = kwargs.get("target_id")
                duration = kwargs.get("duration", 3600)
                expiry = (datetime.utcnow() + timedelta(seconds=int(duration))).isoformat() + "Z"
                
                resp = client.post(
                    f"{base_url}/tickets",
                    headers=headers,
                    json={"user_id": user_id, "target_id": target_id, "expiry": expiry}
                )
                return json.dumps(resp.json())
            
            elif action == "list_ticket_requests":
                resp = client.get(f"{base_url}/ticket-requests", headers=headers)
                return json.dumps(resp.json())
            
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
    
    except Exception as e:
        return json.dumps({"error": str(e)})

# --- Schema ---
WARPGATE_SCHEMA = {
    "name": "warpgate",
    "description": "Manage server access via Warpgate (targets, tickets).",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_targets", "create_ticket", "list_ticket_requests"],
                "description": "Action to perform"
            },
            "user_id": {
                "type": "string",
                "description": "User ID (for create_ticket)"
            },
            "target_id": {
                "type": "string",
                "description": "Target ID (for create_ticket)"
            },
            "duration": {
                "type": "integer",
                "description": "Ticket duration in seconds (default: 3600)"
            }
        },
        "required": ["action"]
    }
}

# --- Registration ---
from tools.registry import registry
registry.register(
    name="warpgate",
    toolset="access",
    schema=WARPGATE_SCHEMA,
    handler=lambda args, **kw: warpgate_tool(
        action=args.get("action", ""),
        **{k: v for k, v in args.items() if k != "action"}
    ),
    check_fn=check_warpgate_requirements,
    requires_env=["WARPGATE_TOKEN"],
)
