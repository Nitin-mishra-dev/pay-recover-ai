"""FastAPI Safety Controls Router."""

from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel
from src.config import settings
from src.core.audit import AuditEventType, audit_ledger
from src.core.telemetry import telemetry


router = APIRouter(prefix="/api/v1/safety", tags=["Safety"])


class SafetyControlsPayload(BaseModel):
    global_kill_switch: bool
    max_retries_ceiling: int
    direct_retry_cost_inr: float
    risk_profile: str = "Balanced"


@router.get("/controls")
async def get_safety_controls() -> Dict[str, Any]:
    """Returns current safety parameters and active telemetry counters."""
    telem = await telemetry.snapshot()
    return {
        "global_kill_switch": settings.global_kill_switch,
        "max_retries_ceiling": settings.max_retries_ceiling,
        "direct_retry_cost_inr": settings.direct_retry_cost_inr,
        "sms_cost_inr": settings.sms_cost_inr,
        "human_ops_cost_inr": settings.human_ops_cost_inr,
        "telemetry": telem
    }


@router.post("/kill-switch")
async def toggle_kill_switch(payload: Dict[str, bool]) -> Dict[str, Any]:
    """Toggles emergency global kill switch."""
    active = payload.get("active", False)
    settings.global_kill_switch = active
    await audit_ledger.record_event(
        AuditEventType.KILL_SWITCH_BLOCKED if active else AuditEventType.SAFETY_CHECK_PASSED,
        {"action": "toggle_kill_switch", "new_state": active}
    )
    return {"global_kill_switch": settings.global_kill_switch}
