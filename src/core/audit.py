"""Cryptographic Tamper-Evident SHA-256 Audit Ledger."""

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.models.audit import AuditBlock, AuditEventType


GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


class AuditLedger:
    """In-memory and persistent tamper-evident cryptographic hash-chained audit ledger."""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._chain: List[AuditBlock] = []
    
    def _compute_payload_hash(self, payload: Dict[str, Any]) -> str:
        canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    
    def _compute_block_hash(
        self,
        sequence_id: int,
        block_id: str,
        timestamp: str,
        event_type: str,
        payload_hash: str,
        previous_hash: str
    ) -> str:
        raw_header = f"{sequence_id}|{block_id}|{timestamp}|{event_type}|{payload_hash}|{previous_hash}"
        return hashlib.sha256(raw_header.encode("utf-8")).hexdigest()
    
    async def record_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        case_id: Optional[str] = None,
        payment_id: Optional[str] = None
    ) -> AuditBlock:
        """Appends an event to the cryptographic ledger with hash-linking."""
        async with self._lock:
            sequence_id = len(self._chain)
            block_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()
            
            previous_hash = self._chain[-1].block_hash if self._chain else GENESIS_HASH
            payload_hash = self._compute_payload_hash(payload)
            
            block_hash = self._compute_block_hash(
                sequence_id=sequence_id,
                block_id=block_id,
                timestamp=timestamp,
                event_type=event_type,
                payload_hash=payload_hash,
                previous_hash=previous_hash
            )
            
            block = AuditBlock(
                sequence_id=sequence_id,
                block_id=block_id,
                case_id=case_id,
                payment_id=payment_id,
                event_type=event_type,
                timestamp=timestamp,
                payload=payload,
                payload_hash=payload_hash,
                previous_hash=previous_hash,
                block_hash=block_hash
            )
            
            self._chain.append(block)
            return block
    
    async def get_chain(self) -> List[AuditBlock]:
        async with self._lock:
            return list(self._chain)
    
    async def verify_chain(self) -> Dict[str, Any]:
        """Audits the entire chain. Detects any modified payload, corrupted hash, or broken sequence."""
        async with self._lock:
            if not self._chain:
                return {"valid": True, "blocks_audited": 0, "errors": []}
            
            errors = []
            for i, block in enumerate(self._chain):
                # 1. Sequence check
                if block.sequence_id != i:
                    errors.append(f"Sequence mismatch at index {i}: expected {i}, got {block.sequence_id}")
                
                # 2. Previous hash check
                expected_prev = self._chain[i - 1].block_hash if i > 0 else GENESIS_HASH
                if block.previous_hash != expected_prev:
                    errors.append(f"Previous hash mismatch at index {i}: expected {expected_prev}, got {block.previous_hash}")
                
                # 3. Payload hash integrity
                computed_payload_hash = self._compute_payload_hash(block.payload)
                if block.payload_hash != computed_payload_hash:
                    errors.append(f"Payload tampered at index {i}: stored {block.payload_hash} != computed {computed_payload_hash}")
                
                # 4. Block hash integrity
                computed_block_hash = self._compute_block_hash(
                    sequence_id=block.sequence_id,
                    block_id=block.block_id,
                    timestamp=block.timestamp,
                    event_type=block.event_type,
                    payload_hash=block.payload_hash,
                    previous_hash=block.previous_hash
                )
                if block.block_hash != computed_block_hash:
                    errors.append(f"Block hash corrupted at index {i}: stored {block.block_hash} != computed {computed_block_hash}")
            
            return {
                "valid": len(errors) == 0,
                "blocks_audited": len(self._chain),
                "errors": errors
            }
    
    async def reset(self) -> None:
        async with self._lock:
            self._chain.clear()


# Global singleton instance
audit_ledger = AuditLedger()
