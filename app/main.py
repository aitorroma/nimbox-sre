from __future__ import annotations

import os
import json
import httpx
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Configuration
NIGHTINGALE_API = os.getenv("NIGHTINGALE_API_URL", "https://collector.nimbox360.com/api/n9e")
NIGHTINGALE_TOKEN = os.getenv("NIGHTINGALE_TOKEN", "")
WARPGATE_API = os.getenv("WARPGATE_API_URL", "https://geo.nimbox360.com/@warpgate/admin/api")
WARPGATE_TOKEN = os.getenv("WARPGATE_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
WIKI_PATH = Path.home() / "nimbox-sre" / "wiki"

app = FastAPI(title="NimBox SRE Agent")


class NightingaleClient:
    def __init__(self):
        self.base_url = NIGHTINGALE_API
        self.headers = {"X-User-Token": NIGHTINGALE_TOKEN}

    async def get_targets(self) -> list[dict]:
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{self.base_url}/targets", headers=self.headers)
            return resp.json().get("dat", {}).get("list", [])

    async def get_alerts(self) -> list[dict]:
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{self.base_url}/alert-cur-events", headers=self.headers)
            return resp.json().get("dat", [])


class WarpgateClient:
    def __init__(self):
        self.base_url = WARPGATE_API
        self.headers = {"X-Warpgate-Token": WARPGATE_TOKEN}

    async def get_targets(self) -> list[dict]:
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{self.base_url}/targets", headers=self.headers)
            return resp.json()

    async def create_ticket(self, user_id: str, target_id: str, duration: int = 3600) -> dict:
        from datetime import timedelta
        expiry = (datetime.utcnow() + timedelta(seconds=duration)).isoformat() + "Z"
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(
                f"{self.base_url}/tickets",
                headers=self.headers,
                json={"user_id": user_id, "target_id": target_id, "expiry": expiry}
            )
            return resp.json()


class WikiManager:
    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        for subdir in ["hosts", "incidents", "runbooks", "decisions"]:
            (self.path / subdir).mkdir(exist_ok=True)

    def log_entry(self, entry_type: str, description: str) -> None:
        log_file = self.path / "log.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## [{timestamp}] {entry_type} | {description}\n"
        with open(log_file, "a") as f:
            f.write(entry)


nightingale = NightingaleClient()
warpgate = WarpgateClient()
wiki = WikiManager(WIKI_PATH)


@app.get("/")
def root() -> dict[str, Any]:
    return {"status": "ok", "service": "nimbox-sre-agent"}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "nightingale_configured": bool(NIGHTINGALE_TOKEN),
        "warpgate_configured": bool(WARPGATE_TOKEN),
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN),
        "wiki_path": str(WIKI_PATH),
    }


@app.get("/api/targets")
async def list_targets():
    targets = await nightingale.get_targets()
    return {"targets": targets, "count": len(targets)}


@app.get("/api/alerts")
async def list_alerts():
    alerts = await nightingale.get_alerts()
    return {"alerts": alerts, "count": len(alerts)}


@app.get("/api/warpgate/targets")
async def list_warpgate_targets():
    targets = await warpgate.get_targets()
    return {"targets": targets}


@app.post("/api/ticket")
async def create_ticket(user_id: str, target_id: str, duration: int = 3600):
    result = await warpgate.create_ticket(user_id, target_id, duration)
    return result


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    
    update = await request.json()
    
    if "message" in update:
        message = update["message"]
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        
        if text == "/targets":
            targets = await nightingale.get_targets()
            response = f"📊 *Hosts monitoreados:* {len(targets)}\n\n"
            for t in targets[:10]:
                name = t.get("name", "unknown")
                host = t.get("host_ip", "?")
                mem = t.get("mem_util", 0)
                response += f"• {name} ({host}) - RAM: {mem:.1f}%\n"
            return {"ok": True, "response": response}
        
        elif text == "/alerts":
            alerts = await nightingale.get_alerts()
            response = f"🚨 *Alertas activas:* {len(alerts)}\n\n"
            for a in alerts[:5]:
                response += f"• {a.get('rule_name', '?')} - {a.get('severity', '?')}\n"
            return {"ok": True, "response": response}
        
        elif text == "/warpgate":
            targets = await warpgate.get_targets()
            return {"ok": True, "response": f"🔐 *Warpgate targets:* {len(targets)}"}
    
    return {"ok": True}
