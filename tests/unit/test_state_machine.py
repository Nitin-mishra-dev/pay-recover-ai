"""Unit tests for the Authoritative Payment State Machine."""

import pytest
from src.core.downtime import rail_sentinel
from src.core.state_machine import state_machine
from src.core.telemetry import telemetry
from src.executor.simulated import simulated_executor
from src.models.events import DowntimeEntity, RazorpayWebhookEvent
from src.models.state import ActionStatus, PaymentState


@pytest.mark.asyncio
async def test_normal_failed_payment_evaluation(make_failed_payment_payload):
    """TEST 1: Valid payment.failed generates candidate actions and schedules recovery."""
    payload = make_failed_payment_payload(payment_id="pay_norm_01", order_id="order_norm_01", amount=500000)
    event = RazorpayWebhookEvent.model_validate(payload)
    
    result = await state_machine.process_webhook_event(event)
    assert result["status"] == "failed_evaluated"
    assert result["selected_action"] == "retry_payment"
    assert result["iev_inr"] > 0
    
    case = await state_machine.get_case_by_payment("pay_norm_01")
    assert case is not None
    assert case.state == PaymentState.DECISION_READY
    assert case.active_action_id == result["action_id"]
    
    # Execute the action via simulated executor
    exec_res = await simulated_executor.execute_action(result["action_id"])
    assert exec_res["success"] is True
    assert exec_res["status"] == "PAYMENT_CAPTURED"
    
    # Case must transition to CAPTURED
    case_after = await state_machine.get_case(case.case_id)
    assert case_after.state == PaymentState.CAPTURED


@pytest.mark.asyncio
async def test_capture_race_cancels_scheduled_action(make_failed_payment_payload, make_captured_payment_payload):
    """TEST 3: payment.failed -> retry scheduled -> payment.captured -> retry cancelled."""
    # Step 1: Failed payment ingests and proposes/schedules retry
    failed_payload = make_failed_payment_payload(payment_id="pay_race_01", order_id="order_race_01")
    failed_event = RazorpayWebhookEvent.model_validate(failed_payload)
    failed_res = await state_machine.process_webhook_event(failed_event)
    action_id = failed_res["action_id"]
    
    # Step 2: Payment captured arrives before execution timer
    captured_payload = make_captured_payment_payload(payment_id="pay_race_01", order_id="order_race_01")
    captured_event = RazorpayWebhookEvent.model_validate(captured_payload)
    cap_res = await state_machine.process_webhook_event(captured_event)
    assert cap_res["status"] == "captured_processed"
    
    # Assert action was cancelled by push cancellation
    action = await state_machine.get_action(action_id)
    assert action.status == ActionStatus.CANCELLED_STALE
    
    stale_count = await telemetry.get_counter("stale_action_rejection_count")
    assert stale_count == 1
    
    # Step 3: Worker tries to execute the cancelled action -> Safety Kernel pulls check and blocks
    exec_res = await simulated_executor.execute_action(action_id)
    assert exec_res["success"] is False
    assert "STAGE_5" in exec_res["reason"]


@pytest.mark.asyncio
async def test_out_of_order_failed_after_captured(make_failed_payment_payload, make_captured_payment_payload):
    """Out-of-order failure event arriving after capture must be discarded (SS-04)."""
    # Capture arrives first
    captured_payload = make_captured_payment_payload(payment_id="pay_ooo_01", order_id="order_ooo_01")
    captured_event = RazorpayWebhookEvent.model_validate(captured_payload)
    await state_machine.process_webhook_event(captured_event)
    
    # Stale failure arrives later
    failed_payload = make_failed_payment_payload(payment_id="pay_ooo_01", order_id="order_ooo_01")
    failed_event = RazorpayWebhookEvent.model_validate(failed_payload)
    failed_res = await state_machine.process_webhook_event(failed_event)
    
    assert failed_res["status"] == "out_of_order_ignored"
    case = await state_machine.get_case_by_payment("pay_ooo_01")
    assert case.state == PaymentState.CAPTURED


@pytest.mark.asyncio
async def test_downtime_adaptive_scheduling(make_failed_payment_payload):
    """Downtime on card rail automatically triggers adaptive delay in retry candidate."""
    # Mark card rail as degraded
    await rail_sentinel.record_downtime_started(DowntimeEntity(
        id="down_001",
        method="card",
        status="started",
        severity="HIGH"
    ))
    
    payload = make_failed_payment_payload(payment_id="pay_dt_01", order_id="order_dt_01")
    event = RazorpayWebhookEvent.model_validate(payload)
    
    res = await state_machine.process_webhook_event(event)
    action = await state_machine.get_action(res["action_id"])
    
    # Retry delay must be increased due to degradation
    assert action.action_parameters["delay_seconds"] >= 1800
