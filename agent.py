#!/usr/bin/env python3
"""
NimBox SRE Agent
AI SRE Agent for nimbox360 infrastructure
Based on Hermes Agent pattern + Karpathy Wiki
"""

import os
import json
import httpx
from pathlib import Path
from datetime import datetime
from typing import Optional

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Configuration
NIGHTINGALE_API = os.getenv("NIGHTINGALE_API_URL", "https://collector.nimbox360.com/api/n9e")
NIGHTINGALE_TOKEN = os.getenv("NIGHTINGALE_TOKEN", "")
WARPGATE_API = os.getenv("WARPGATE_API_URL", "https://geo.nimbox360.com/@warpgate/admin/api")
WARPGATE_TOKEN = os.getenv("WARPGATE_TOKEN", "a92f8d50c16a057e67bde9674344aba99cb7de372df5c20d70a9ef527cfe4723")
WIKI_PATH = Path.home() / "nimbox-sre" / "wiki"


class NightingaleClient:
    """Cliente para Nightingale API"""
    
    def __init__(self):
        self.base_url = NIGHTINGALE_API
        self.headers = {"Authorization": f"Bearer {NIGHTINGALE_TOKEN}"}
    
    async def get_targets(self):
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{self.base_url}/targets", headers=self.headers)
            return resp.json().get("dat", {}).get("list", [])
    
    async def get_alerts(self):
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{self.base_url}/alert-cur-events", headers=self.headers)
            return resp.json().get("dat", [])


class WarpgateClient:
    """Cliente para Warpgate API"""
    
    def __init__(self):
        self.base_url = WARPGATE_API
        self.headers = {"X-Warpgate-Token": WARPGATE_TOKEN}
    
    async def create_ticket(self, user_id, target_id, duration=3600):
        from datetime import datetime, timedelta
        expiry = (datetime.utcnow() + timedelta(seconds=duration)).isoformat() + "Z"
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(
                f"{self.base_url}/tickets",
                headers=self.headers,
                json={"user_id": user_id, "target_id": target_id, "expiry": expiry}
            )
            return resp.json()


class WikiManager:
    """Gestor de wiki siguiendo patrón Karpathy"""
    
    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / "hosts").mkdir(exist_ok=True)
        (self.path / "incidents").mkdir(exist_ok=True)
        (self.path / "runbooks").mkdir(exist_ok=True)
        (self.path / "decisions").mkdir(exist_ok=True)
    
    def log_entry(self, entry_type, description):
        """Agregar entrada al log"""
        log_file = self.path / "log.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## [{timestamp}] {entry_type} | {description}\n"
        with open(log_file, "a") as f:
            f.write(entry)
    
    def create_incident(self, hostname, cause, timeline, fix, prevention):
        """Crear página de incidente"""
        date = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date}-{hostname}-{cause[:30].replace(' ', '-')}.md"
        content = f"""# Incidente: {hostname} - {cause}

## Fecha
{datetime.now().strftime("%Y-%m-%d %H:%M")}

## Timeline
{timeline}

## Causa Raíz
{cause}

## Fix Aplicado
{fix}

## Prevención
{prevention}
"""
        filepath = self.path / "incidents" / filename
        filepath.write_text(content)
        self.log_entry("incident", f"{hostname} - {cause}")
        return filepath
    
    def create_runbook(self, name, steps, prerequisites="", rollback=""):
        """Crear runbook"""
        filename = f"{name.replace(' ', '-').lower()}.md"
        content = f"""# Runbook: {name}

## Prerrequisitos
{prerequisites}

## Pasos
{steps}

## Rollback
{rollback}
"""
        filepath = self.path / "runbooks" / filename
        filepath.write_text(content)
        self.log_entry("runbook", f"Created: {name}")
        return filepath


async def main():
    """Función principal del agente"""
    print("=== NimBox SRE Agent ===")
    print(f"Wiki: {WIKI_PATH}")
    print()
    
    # Initialize clients
    nightingale = NightingaleClient()
    warpgate = WarpgateClient()
    wiki = WikiManager(WIKI_PATH)
    
    # Check targets
    print("Checking targets...")
    targets = await nightingale.get_targets()
    print(f"Found {len(targets)} targets")
    
    # Check alerts
    print("Checking alerts...")
    alerts = await nightingale.get_alerts()
    print(f"Found {len(alerts)} active alerts")
    
    # Log
    wiki.log_entry("startup", f"Agent started, {len(targets)} targets, {len(alerts)} alerts")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
