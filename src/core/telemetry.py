"""Runtime Atomic Safety Telemetry Counters."""

import asyncio
from typing import Dict


class SafetyTelemetry:
    """Thread-safe, atomic runtime safety telemetry counters."""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._counters: Dict[str, int] = {
            "duplicate_event_count": 0,
            "duplicate_execution_attempt_count": 0,
            "stale_action_rejection_count": 0,
            "unauthorized_action_count": 0,
            "kill_switch_rejection_count": 0,
            "policy_validation_failure_count": 0,
            "partial_execution_count": 0,
        }
    
    async def increment(self, counter_name: str, amount: int = 1) -> int:
        async with self._lock:
            if counter_name not in self._counters:
                self._counters[counter_name] = 0
            self._counters[counter_name] += amount
            return self._counters[counter_name]
    
    async def get_counter(self, counter_name: str) -> int:
        async with self._lock:
            return self._counters.get(counter_name, 0)
    
    async def snapshot(self) -> Dict[str, int]:
        async with self._lock:
            return dict(self._counters)
    
    async def reset(self) -> None:
        async with self._lock:
            for k in self._counters:
                self._counters[k] = 0


# Global singleton instance for the running runtime
telemetry = SafetyTelemetry()
