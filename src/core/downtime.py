"""Payment Rail Health Sentinel tracking Razorpay downtime webhooks."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional
from src.models.events import DowntimeEntity


class PaymentRailHealthSentinel:
    """Tracks active gateway, bank, and payment network degradation."""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        # Key: (method, bank_or_network) -> DowntimeEntity
        self._active_downtimes: Dict[str, DowntimeEntity] = {}
    
    def _make_key(self, method: str, bank: Optional[str] = None, network: Optional[str] = None) -> str:
        identifier = bank or network or "global"
        return f"{method.lower()}:{identifier.lower()}"
    
    async def record_downtime_started(self, entity: DowntimeEntity) -> None:
        async with self._lock:
            key = self._make_key(entity.method, entity.bank, entity.network)
            self._active_downtimes[key] = entity
    
    async def record_downtime_resolved(self, method: str, bank: Optional[str] = None, network: Optional[str] = None) -> None:
        async with self._lock:
            key = self._make_key(method, bank, network)
            self._active_downtimes.pop(key, None)
    
    async def is_rail_degraded(self, method: str, bank: Optional[str] = None, network: Optional[str] = None) -> bool:
        async with self._lock:
            key = self._make_key(method, bank, network)
            if key in self._active_downtimes:
                return True
            m_prefix = f"{method.lower()}:"
            return any(k.startswith(m_prefix) for k in self._active_downtimes)
    
    async def get_adaptive_delay(self, method: str, bank: Optional[str] = None, network: Optional[str] = None, default_delay: int = 300) -> int:
        """Returns increased delay if rail is currently degraded."""
        async with self._lock:
            key = self._make_key(method, bank, network)
            target_dt = self._active_downtimes.get(key)
            if not target_dt:
                m_prefix = f"{method.lower()}:"
                for k, dt in self._active_downtimes.items():
                    if k.startswith(m_prefix):
                        target_dt = dt
                        break
            if target_dt:
                now_ts = int(datetime.now(timezone.utc).timestamp())
                if target_dt.end and target_dt.end > now_ts:
                    return max(default_delay, (target_dt.end - now_ts) + 300)
                return max(default_delay, 1800)  # Default 30 min during open-ended downtime
            return default_delay
    
    async def reset(self) -> None:
        async with self._lock:
            self._active_downtimes.clear()


# Global singleton instance
rail_sentinel = PaymentRailHealthSentinel()
