"""Unit tests for the Policy Engine and Decision Schema Validator."""

import pytest
from src.core.safety_gate import safety_kernel
from src.core.state_machine import state_machine
from src.core.telemetry import telemetry
from src.executor.simulated import simulated_executor
from src.models.events import RazorpayWebhookEvent


@pytest.mark.asyncio
async def test_malformed_llm_json_fails_closed(make_failed_payment_payload):
    """TEST 7: Malformed or uncontracted LLM decisions fail closed at Stage 1."""
    payload = make_failed_payment_payload(payment_id="pay_mal_01", order_id="order_mal_01")
    event = RazorpayWebhookEvent.model_validate(payload)
    res = await state_machine.process_webhook_event(event)
    action_id = res["action_id"]
    
    # Simulate a hallucinated/malformed LLM output dict
    malformed_decision = {
        "decision_id": "invalid_uuid",
        "action": "grant_free_money_and_bonus",  # Non-contracted enum
        "expected_recovery_amount": -500.0,      # Invalid negative amount
        "reason_codes": []                       # Missing min_length=1
    }
    
    exec_res = await simulated_executor.execute_action(action_id, raw_decision_dict=malformed_decision)
    assert exec_res["success"] is False
    assert "STAGE_1_SCHEMA_INVALID" in exec_res["reason"]
    
    schema_err_count = await telemetry.get_counter("policy_validation_failure_count")
    assert schema_err_count == 1
