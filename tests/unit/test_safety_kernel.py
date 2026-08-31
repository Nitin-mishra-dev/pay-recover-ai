"""Unit tests for the 8-Stage Deterministic Safety Kernel."""

import pytest
from src.config import settings
from src.core.safety_gate import safety_kernel
from src.core.state_machine import state_machine
from src.core.telemetry import telemetry
from src.executor.simulated import simulated_executor
from src.models.events import RazorpayWebhookEvent
from src.models.state import PaymentState


@pytest.mark.asyncio
async def test_kill_switch_halts_execution(make_failed_payment_payload):
    """TEST 5: Global kill switch immediately halts all action dispatch."""
    payload = make_failed_payment_payload(payment_id="pay_ks_01", order_id="order_ks_01")
    event = RazorpayWebhookEvent.model_validate(payload)
    res = await state_machine.process_webhook_event(event)
    action_id = res["action_id"]
    
    # Activate emergency kill switch
    settings.global_kill_switch = True
    
    exec_res = await simulated_executor.execute_action(action_id)
    assert exec_res["success"] is False
    assert "KILL_SWITCH" in exec_res["reason"]
    
    ks_count = await telemetry.get_counter("kill_switch_rejection_count")
    assert ks_count == 1


@pytest.mark.asyncio
async def test_retry_ceiling_blocks_action(make_failed_payment_payload):
    """TEST 6: Attempts >= max_retries_ceiling causes Safety Gate rejection."""
    payload = make_failed_payment_payload(payment_id="pay_ceil_01", order_id="order_ceil_01")
    event = RazorpayWebhookEvent.model_validate(payload)
    res = await state_machine.process_webhook_event(event)
    action_id = res["action_id"]
    
    # Set attempt_count to ceiling (3)
    case = await state_machine.get_case_by_payment("pay_ceil_01")
    case.attempt_count = 3
    
    exec_res = await simulated_executor.execute_action(action_id)
    assert exec_res["success"] is False
    assert "STAGE_4_RETRY_CEILING_REACHED" in exec_res["reason"]
    
    unauth_count = await telemetry.get_counter("unauthorized_action_count")
    assert unauth_count == 1
    
    # Case must transition to STOPPED
    case_after = await state_machine.get_case(case.case_id)
    assert case_after.state == PaymentState.STOPPED


@pytest.mark.asyncio
async def test_dispute_halts_recovery(make_failed_payment_payload):
    """Dispute creation freezes case and prevents execution."""
    payload = make_failed_payment_payload(payment_id="pay_disp_01", order_id="order_disp_01")
    event = RazorpayWebhookEvent.model_validate(payload)
    res = await state_machine.process_webhook_event(event)
    action_id = res["action_id"]
    
    # Dispute event arrives
    dispute_payload = {
        "entity": "event",
        "account_id": "acc_merch_01",
        "event": "payment.dispute.created",
        "contains": ["payment", "dispute"],
        "payload": {
            "payment": {"entity": {"id": "pay_disp_01", "order_id": "order_disp_01", "amount": 450000}}
        }
    }
    await state_machine.process_webhook_event(RazorpayWebhookEvent.model_validate(dispute_payload))
    
    exec_res = await simulated_executor.execute_action(action_id)
    assert exec_res["success"] is False
    assert "DISPUTED" in exec_res["reason"]
