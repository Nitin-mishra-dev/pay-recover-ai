"""Integration tests for Concurrency Races and Idempotency Invariants."""

import asyncio
import pytest
from src.core.idempotency import idempotency_manager
from src.core.safety_gate import safety_kernel
from src.core.state_machine import state_machine
from src.core.telemetry import telemetry
from src.executor.simulated import simulated_executor
from src.models.events import RazorpayWebhookEvent
from src.models.state import PaymentState


@pytest.mark.asyncio
async def test_concurrent_worker_execution_race(make_failed_payment_payload):
    """TEST 4: Concurrent parallel execution workers race for the same action -> exactly 1 succeeds, 0 double executions."""
    payload = make_failed_payment_payload(payment_id="pay_conc_01", order_id="order_conc_01")
    event = RazorpayWebhookEvent.model_validate(payload)
    res = await state_machine.process_webhook_event(event)
    action_id = res["action_id"]
    
    # Launch 10 simultaneous execution worker tasks
    tasks = [simulated_executor.execute_action(action_id) for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    # Assert exactly 1 succeeded and 9 were blocked
    success_count = sum(1 for r in results if r["success"] is True)
    blocked_count = sum(1 for r in results if r["success"] is False)
    
    assert success_count == 1
    assert blocked_count == 9
    
    # Telemetry check: 9 duplicate execution attempts / stale executions were caught and prevented
    stale_rejections = await telemetry.get_counter("stale_action_rejection_count")
    dup_exec_attempts = await telemetry.get_counter("duplicate_execution_attempt_count")
    assert (stale_rejections + dup_exec_attempts) == 9
    assert await telemetry.get_counter("unsafe_execution_count") == 0
    
    # Payment state must be cleanly CAPTURED
    case = await state_machine.get_case_by_payment("pay_conc_01")
    assert case.state == PaymentState.CAPTURED


@pytest.mark.asyncio
async def test_action_idempotency_lock_direct_conflict(make_failed_payment_payload):
    """Stage 6: Pre-acquired idempotency lock blocks execution and increments duplicate_execution_attempt_count."""
    payload = make_failed_payment_payload(payment_id="pay_idem_01", order_id="order_idem_01")
    event = RazorpayWebhookEvent.model_validate(payload)
    res = await state_machine.process_webhook_event(event)
    action_id = res["action_id"]
    
    action = await state_machine.get_action(action_id)
    # Pre-acquire the idempotency lock externally
    await idempotency_manager.try_acquire_action_lock(action.idempotency_key)
    
    # Attempt execution -> must be blocked at Stage 6
    exec_res = await simulated_executor.execute_action(action_id)
    assert exec_res["success"] is False
    assert "STAGE_6_IDEMPOTENCY_CONFLICT" in exec_res["reason"]
    
    dup_attempts = await telemetry.get_counter("duplicate_execution_attempt_count")
    assert dup_attempts == 1


@pytest.mark.asyncio
async def test_concurrent_capture_and_retry_race(make_failed_payment_payload, make_captured_payment_payload):
    """Concurrent capture webhook and retry execution -> payment captured wins, zero duplicate charges."""
    failed_payload = make_failed_payment_payload(payment_id="pay_race_sim_01", order_id="order_race_sim_01")
    failed_event = RazorpayWebhookEvent.model_validate(failed_payload)
    failed_res = await state_machine.process_webhook_event(failed_event)
    action_id = failed_res["action_id"]
    
    captured_payload = make_captured_payment_payload(payment_id="pay_race_sim_01", order_id="order_race_sim_01")
    captured_event = RazorpayWebhookEvent.model_validate(captured_payload)
    
    # Fire capture webhook and retry execution concurrently
    cap_task = state_machine.process_webhook_event(captured_event)
    exec_task = simulated_executor.execute_action(action_id)
    
    cap_res, exec_res = await asyncio.gather(cap_task, exec_task)
    
    case = await state_machine.get_case_by_payment("pay_race_sim_01")
    assert case.state == PaymentState.CAPTURED
