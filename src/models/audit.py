"""Cryptographic Tamper-Evident SHA-256 Audit Log Models."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AuditEventType:
    WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED"
    WEBHOOK_DUPLICATE_IGNORED = "WEBHOOK_DUPLICATE_IGNORED"
    PAYMENT_FAILED_OBSERVED = "PAYMENT_FAILED_OBSERVED"
    PAYMENT_CAPTURED_OBSERVED = "PAYMENT_CAPTURED_OBSERVED"
    DECISION_EVALUATED = "DECISION_EVALUATED"
    SAFETY_CHECK_PASSED = "SAFETY_CHECK_PASSED"
    SAFETY_CHECK_FAILED = "SAFETY_CHECK_FAILED"
    ACTION_SCHEDULED = "ACTION_SCHEDULED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    STALE_ACTION_CANCELLED = "STALE_ACTION_CANCELLED"
    KILL_SWITCH_BLOCKED = "KILL_SWITCH_BLOCKED"
    DOWNTIME_STARTED = "DOWNTIME_STARTED"
    DOWNTIME_RESOLVED = "DOWNTIME_RESOLVED"


class AuditBlock(BaseModel):
    """A tamper-evident hash-chained block representing an immutable lifecycle event."""
    
    sequence_id: int = Field(description="Strict monotonically increasing integer")
    block_id: str = Field(description="Unique block UUID")
    case_id: Optional[str] = None
    payment_id: Optional[str] = None
    event_type: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: Dict[str, Any] = Field(default_factory=dict)
    payload_hash: str = Field(description="SHA-256 hash of canonical JSON payload")
    previous_hash: str = Field(description="Hash of sequence_id - 1 block (Genesis if seq=0)")
    block_hash: str = Field(description="SHA-256 hash of this entire block header & hashes")
