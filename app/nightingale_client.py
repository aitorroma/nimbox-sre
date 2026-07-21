"""Nightingale API client for monitoring data"""
import httpx
from typing import Optional
from .config import settings


class NightingaleClient:
    def __init__(self):
        self.base_url = settings.nightingale_api_url
        self.token = settings.nightingale_token
        self.headers = {
            "X-User-Token": self.token,
            "Content-Type": "application/json"
        }
    
    async def get_targets(self) -> list[dict]:
        """Get all monitored targets"""
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{self.base_url}/targets", headers=self.headers)
            resp.raise_for_status()
            return resp.json().get("dat", {}).get("list", [])
    
    async def get_target(self, target_id: str) -> dict:
        """Get specific target details"""
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{self.base_url}/targets/{target_id}", headers=self.headers)
            resp.raise_for_status()
            return resp.json().get("dat", {})
    
    async def get_active_alerts(self) -> list[dict]:
        """Get active alerts"""
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{self.base_url}/alert-cur-events", headers=self.headers)
            resp.raise_for_status()
            return resp.json().get("dat", [])
    
    async def get_alert_rules(self) -> list[dict]:
        """Get alert rules"""
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{self.base_url}/alert-rules", headers=self.headers)
            resp.raise_for_status()
            return resp.json().get("dat", [])
    
    async def get_busi_groups(self) -> list[dict]:
        """Get business groups"""
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{self.base_url}/busi-groups", headers=self.headers)
            resp.raise_for_status()
            return resp.json().get("dat", [])
