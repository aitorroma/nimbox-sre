from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HostStatus(BaseModel):
    """Estado de un host monitoreado"""
    name: str
    host: str
    status: str  # up, down, warning
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_percent: Optional[float] = None
    last_check: Optional[datetime] = None


class Alert(BaseModel):
    """Alerta de Nightingale"""
    id: str
    rule_name: str
    severity: str  # critical, warning, info
    status: str  # firing, resolved
    message: str
    labels: dict = {}
    annotations: dict = {}
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None


class Investigation(BaseModel):
    """Resultado de investigación"""
    alert_id: str
    root_cause: str
    evidence: list[str] = []
    recommended_actions: list[str] = []
    auto_fixable: bool = False


class TicketRequest(BaseModel):
    """Solicitud de ticket Warpgate"""
    target_id: str
    target_name: str
    user_id: str
    duration_seconds: int = 3600
    reason: str = ""
