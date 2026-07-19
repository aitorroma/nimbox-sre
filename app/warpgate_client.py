"""Warpgate API client for server access"""
import httpx
from typing import Optional
from .config import settings


class WarpgateClient:
    def __init__(self):
        self.base_url = settings.warpgate_api_url
        self.token = settings.warpgate_token
        self.headers = {
            "X-Warpgate-Token": self.token,
            "Content-Type": "application/json"
        }
    
    async def get_targets(self) -> list[dict]:
        """Get all available targets"""
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{self.base_url}/targets", headers=self.headers)
            resp.raise_for_status()
            return resp.json().get("dat", [])
    
    async def create_ticket(self, user_id: str, target_id: str, duration: int = 3600) -> dict:
        """Create a ticket for server access"""
        from datetime import datetime, timedelta
        expiry = (datetime.utcnow() + timedelta(seconds=duration)).isoformat() + "Z"
        
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(
                f"{self.base_url}/tickets",
                headers=self.headers,
                json={
                    "user_id": user_id,
                    "target_id": target_id,
                    "expiry": expiry
                }
            )
            resp.raise_for_status()
            return resp.json()
    
    async def get_ticket_requests(self) -> list[dict]:
        """Get pending ticket requests"""
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{self.base_url}/ticket-requests", headers=self.headers)
            resp.raise_for_status()
            return resp.json().get("dat", [])
