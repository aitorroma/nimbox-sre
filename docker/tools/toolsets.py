"""Toolsets for SRE Agent."""

# Core tools available on all platforms
_HERMES_CORE_TOOLS = [
    "nightingale",
    "warpgate",
    "opensre",
]

# Toolset definitions
TOOLSETS = {
    "monitoring": {
        "description": "Monitoring tools for Nightingale",
        "tools": ["nightingale"],
        "includes": []
    },
    "access": {
        "description": "Server access tools for Warpgate",
        "tools": ["warpgate"],
        "includes": []
    },
    "investigation": {
        "description": "Incident investigation tools for OpenSRE",
        "tools": ["opensre"],
        "includes": []
    },
    "sre": {
        "description": "SRE tools (monitoring + access + investigation)",
        "tools": ["nightingale", "warpgate", "opensre"],
        "includes": ["monitoring", "access", "investigation"]
    }
}
