"""Unit tests for the Cryptographic Tamper-Evident SHA-256 Audit Ledger."""

import pytest
from src.core.audit import audit_ledger


@pytest.mark.asyncio
async def test_audit_hash_chain_integrity():
    """Sequentially recorded blocks form a cryptographically unbroken hash chain."""
    await audit_ledger.record_event("EVENT_A", {"key": "value_1"})
    await audit_ledger.record_event("EVENT_B", {"key": "value_2"})
    await audit_ledger.record_event("EVENT_C", {"key": "value_3"})
    
    chain = await audit_ledger.get_chain()
    assert len(chain) == 3
    
    # Block 1 previous_hash must match Block 0 block_hash
    assert chain[1].previous_hash == chain[0].block_hash
    # Block 2 previous_hash must match Block 1 block_hash
    assert chain[2].previous_hash == chain[1].block_hash
    
    audit_res = await audit_ledger.verify_chain()
    assert audit_res["valid"] is True
    assert audit_res["blocks_audited"] == 3
    assert len(audit_res["errors"]) == 0


@pytest.mark.asyncio
async def test_audit_tamper_detection():
    """Modifying a historical payload breaks payload hash and block hash verification."""
    await audit_ledger.record_event("EVENT_1", {"amount": 1000})
    await audit_ledger.record_event("EVENT_2", {"amount": 2000})
    
    chain = await audit_ledger.get_chain()
    # Maliciously modify Block 0's payload in memory
    chain[0].payload["amount"] = 999999
    
    audit_res = await audit_ledger.verify_chain()
    assert audit_res["valid"] is False
    assert len(audit_res["errors"]) > 0
    assert any("Payload tampered" in err for err in audit_res["errors"])
