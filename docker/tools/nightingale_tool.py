"""Nightingale Tool -- query monitoring data from Nightingale."""
import json
import os
import logging

logger = logging.getLogger(__name__)

# --- Availability check ---
def check_nightingale_requirements() -> bool:
    """Return True if the tool's dependencies are available."""
    return bool(os.getenv("NIGHTINGALE_TOKEN"))

# --- Handler ---
def nightingale_tool(action: str, **kwargs) -> str:
    """Query Nightingale monitoring data."""
    import httpx
    
    token = os.getenv("NIGHTINGALE_TOKEN")
    base_url = os.getenv("NIGHTINGALE_API_URL", "https://collector.nimbox360.com/api/n9e")
    
    if not token:
        return json.dumps({"error": "NIGHTINGALE_TOKEN not configured"})
    
    headers = {"X-User-Token": token}
    
    try:
        with httpx.Client(verify=False) as client:
            if action == "list_targets":
                resp = client.get(f"{base_url}/targets", headers=headers)
                data = resp.json()
                targets = data.get("dat", {}).get("list", [])
                return json.dumps({"targets": targets, "count": len(targets)})
            
            elif action == "get_target":
                target_id = kwargs.get("target_id")
                resp = client.get(f"{base_url}/targets/{target_id}", headers=headers)
                return json.dumps(resp.json())
            
            elif action == "list_alerts":
                resp = client.get(f"{base_url}/alert-cur-events", headers=headers)
                data = resp.json()
                alerts = data.get("dat", [])
                return json.dumps({"alerts": alerts, "count": len(alerts)})
            
            elif action == "list_alert_rules":
                resp = client.get(f"{base_url}/alert-rules", headers=headers)
                data = resp.json()
                rules = data.get("dat", [])
                return json.dumps({"rules": rules, "count": len(rules)})
            
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
    
    except Exception as e:
        return json.dumps({"error": str(e)})

# --- Schema ---
NIGHTINGALE_SCHEMA = {
    "name": "nightingale",
    "description": "Query Nightingale monitoring data (targets, alerts, rules).",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_targets", "get_target", "list_alerts", "list_alert_rules"],
                "description": "Action to perform"
            },
            "target_id": {
                "type": "string",
                "description": "Target ID (for get_target action)"
            }
        },
        "required": ["action"]
    }
}

# --- Registration ---
from tools.registry import registry
registry.register(
    name="nightingale",
    toolset="monitoring",
    schema=NIGHTINGALE_SCHEMA,
    handler=lambda args, **kw: nightingale_tool(
        action=args.get("action", ""),
        **{k: v for k, v in args.items() if k != "action"}
    ),
    check_fn=check_nightingale_requirements,
    requires_env=["NIGHTINGALE_TOKEN"],
)
