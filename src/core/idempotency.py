"""Two-tier idempotency management: external webhook events & internal action execution."""

import asyncio
import hashlib
import json
from typing import Any, Dict, Set


class IdempotencyManager:
    """Manages event deduplication and action execution locks."""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._seen_event_ids: Set[str] = set()
        self._acquired_action_locks: Set[str] = set()
    
    async def try_acquire_event(self, event_id: str) -> bool:
        """Atomically claim an event ID. Returns True if first time, False if duplicate."""
        async with self._lock:
            if event_id in self._seen_event_ids:
                return False
            self._seen_event_ids.add(event_id)
            return True
    
    def compute_action_idempotency_key(
        self,
        merchant_id: str,
        payment_id: str,
        action_type: str,
        action_parameters: Dict[str, Any],
        decision_version: str = "v1"
    ) -> str:
        """Computes deterministic SHA-256 action key."""
        canonical_params = json.dumps(action_parameters, sort_keys=True, separators=(',', ':'))
        raw = f"{merchant_id}:{payment_id}:{action_type}:{canonical_params}:{decision_version}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
    
    async def try_acquire_action_lock(self, idempotency_key: str) -> bool:
        """Atomically acquires execution lock for an action. Returns False if already executed/locked."""
        async with self._lock:
            if idempotency_key in self._acquired_action_locks:
                return False
            self._acquired_action_locks.add(idempotency_key)
            return True
    
    async def reset(self) -> None:
        async with self._lock:
            self._seen_event_ids.clear()
            self._acquired_action_locks.clear()


# Global singleton instance
idempotency_manager = IdempotencyManager()
