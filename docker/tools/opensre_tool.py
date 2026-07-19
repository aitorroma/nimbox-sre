"""OpenSRE Tool -- investigate incidents with OpenSRE."""
import json
import os
import logging

logger = logging.getLogger(__name__)

# --- Availability check ---
def check_opensre_requirements() -> bool:
    """Return True if the tool's dependencies are available."""
    return bool(os.getenv("OPENSRE_URL"))

# --- Handler ---
def opensre_tool(action: str, **kwargs) -> str:
    """Investigate incidents with OpenSRE."""
    import httpx
    
    base_url = os.getenv("OPENSRE_URL", "https://sre.nimbox360.com")
    
    try:
        with httpx.Client(verify=False) as client:
            if action == "health":
                resp = client.get(f"{base_url}/health")
                return json.dumps(resp.json())
            
            elif action == "investigate":
                alert = kwargs.get("alert", "")
                resp = client.post(
                    f"{base_url}/investigate",
                    json={"alert": alert}
                )
                return json.dumps(resp.json())
            
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
    
    except Exception as e:
        return json.dumps({"error": str(e)})

# --- Schema ---
OPENSRE_SCHEMA = {
    "name": "opensre",
    "description": "Investigate incidents with OpenSRE.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["health", "investigate"],
                "description": "Action to perform"
            },
            "alert": {
                "type": "string",
                "description": "Alert description (for investigate)"
            }
        },
        "required": ["action"]
    }
}

# --- Registration ---
from tools.registry import registry
registry.register(
    name="opensre",
    toolset="investigation",
    schema=OPENSRE_SCHEMA,
    handler=lambda args, **kw: opensre_tool(
        action=args.get("action", ""),
        **{k: v for k, v in args.items() if k != "action"}
    ),
    check_fn=check_opensre_requirements,
    requires_env=["OPENSRE_URL"],
)
