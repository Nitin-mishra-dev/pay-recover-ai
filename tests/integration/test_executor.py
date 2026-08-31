"""Integration tests for Simulated Executor and Gateway Timeouts."""

import pytest
from src.core.state_machine import state_machine
from src.core.telemetry import telemetry
from src.executor.simulated import SimulatedExecutor
from src.models.events import RazorpayWebhookEvent


@pytest.mark.asyncio
async def test_gateway_timeout_fail_safe(make_failed_payment_payload):
    """HTTP 504 Gateway Timeout safely buffers action without blind re-attempt (SS-10)."""
    payload = make_failed_payment_payload(payment_id="pay_504_01", order_id="order_504_01")
    event = RazorpayWebhookEvent.model_validate(payload)
    res = await state_machine.process_webhook_event(event)
    action_id = res["action_id"]
    
    # Initialize executor configured to simulate HTTP 504 gateway timeout
    timeout_executor = SimulatedExecutor(simulate_network_timeout=True)
    exec_res = await timeout_executor.execute_action(action_id)
    
    assert exec_res["success"] is False
    assert exec_res["status"] == "GATEWAY_TIMEOUT"
    
    # Telemetry: partial execution counters incremented & contained safely
    assert await telemetry.get_counter("partial_execution_injected_count") == 1
    assert await telemetry.get_counter("partial_execution_contained_count") == 1
    assert await telemetry.get_counter("partial_execution_count") == 1
    assert await telemetry.get_counter("unsafe_execution_count") == 0
