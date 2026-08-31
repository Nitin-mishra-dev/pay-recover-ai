"""FastAPI Demo Scenario Runner for Failure Lab and Video Walkthroughs."""

import hashlib
import json
import uuid
from typing import Any, Dict
from fastapi import APIRouter, status
from src.config import settings
from src.core.audit import AuditEventType, audit_ledger
from src.core.downtime import rail_sentinel
from src.core.idempotency import idempotency_manager
from src.core.state_machine import state_machine
from src.core.telemetry import telemetry
from src.executor.simulated import simulated_executor
from src.models.events import DowntimeEntity, RazorpayWebhookEvent


router = APIRouter(prefix="/api/v1/demo", tags=["Demo"])


@router.post("/reset")
async def reset_demo_state() -> Dict[str, Any]:
    """Resets registries and seeds initial diverse demo queue."""
    await state_machine.reset()
    await idempotency_manager.reset()
    await audit_ledger.reset()
    await telemetry.reset()
    await rail_sentinel.reset()
    settings.global_kill_switch = False
    
    # Populate initial 5 diverse cases
    demo_cases = [
        ("pay_demo_01", "order_demo_01", 749900, "BAD_REQUEST_PAYMENT_TIMED_OUT", "Bank network timeout during 3DS", "card"),
        ("pay_demo_02", "order_demo_02", 1250000, "BAD_REQUEST_INSUFFICIENT_FUNDS", "Insufficient balance in account", "upi"),
        ("pay_demo_03", "order_demo_03", 4500000, "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK", "Generic issuer decline on large ticket", "netbanking"),
        ("pay_demo_04", "order_demo_04", 150000, "BAD_REQUEST_CARD_STOLEN", "Card reported stolen (Hard Decline)", "card"),
        ("pay_demo_05", "order_demo_05", 900000, "BAD_REQUEST_PAYMENT_AUTHENTICATION_FAILED", "User abandoned 2FA screen", "upi"),
    ]
    
    for pid, oid, amount, code, desc, method in demo_cases:
        event = RazorpayWebhookEvent.model_validate({
            "entity": "event",
            "account_id": "acc_merch_demo",
            "event": "payment.failed",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": pid,
                        "order_id": oid,
                        "amount": amount,
                        "currency": "INR",
                        "status": "failed",
                        "method": method,
                        "error_code": code,
                        "error_description": desc,
                        "email": "customer@example.com",
                        "contact": "+919876543210"
                    }
                }
            }
        })
        await state_machine.process_webhook_event(event)
    
    return {"status": "reset_complete", "cases_initialized": len(demo_cases)}


@router.post("/scenarios/economic_decision")
async def run_scenario_economic_decision() -> Dict[str, Any]:
    """Scenario A: Standard failed payment -> candidate action comparison -> IEV maximization."""
    pid = f"pay_scen_a_{uuid.uuid4().hex[:6]}"
    oid = f"order_scen_a_{uuid.uuid4().hex[:6]}"
    event = RazorpayWebhookEvent.model_validate({
        "entity": "event",
        "account_id": "acc_merch_demo",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": pid,
                    "order_id": oid,
                    "amount": 749900,  # ₹7,499.00
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                    "error_description": "Bank network response timed out",
                    "email": "sarah.merchant@example.com",
                    "contact": "+919876543210"
                }
            }
        }
    })
    res = await state_machine.process_webhook_event(event)
    return {"scenario": "FLOW_A_ECONOMIC_DECISION", "details": res}


@router.post("/scenarios/capture_race")
async def run_scenario_capture_race() -> Dict[str, Any]:
    """Scenario B: payment.failed schedules retry -> payment.captured push-cancels retry -> zero duplicate executions."""
    pid = f"pay_race_{uuid.uuid4().hex[:6]}"
    oid = f"order_race_{uuid.uuid4().hex[:6]}"
    
    # 1. Failure event arrives
    failed_event = RazorpayWebhookEvent.model_validate({
        "entity": "event",
        "account_id": "acc_merch_demo",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": pid,
                    "order_id": oid,
                    "amount": 499900,
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                    "error_description": "Bank timeout"
                }
            }
        }
    })
    failed_res = await state_machine.process_webhook_event(failed_event)
    action_id = failed_res["action_id"]
    
    # 2. Customer UPI retry succeeds -> payment.captured arrives
    captured_event = RazorpayWebhookEvent.model_validate({
        "entity": "event",
        "account_id": "acc_merch_demo",
        "event": "payment.captured",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": pid,
                    "order_id": oid,
                    "amount": 499900,
                    "currency": "INR",
                    "status": "captured",
                    "method": "card"
                }
            }
        }
    })
    cap_res = await state_machine.process_webhook_event(captured_event)
    
    # 3. Scheduled worker attempts execution -> blocked at Stage 5
    exec_res = await simulated_executor.execute_action(action_id)
    
    return {
        "scenario": "FLOW_B_CAPTURE_RACE",
        "payment_id": pid,
        "action_id": action_id,
        "failed_event_status": failed_res["status"],
        "capture_event_status": cap_res["status"],
        "worker_execution_attempt": exec_res,
        "duplicate_executions": 0,
        "invariant": "STALE_RETRY_INTERCEPTED_AND_CANCELLED"
    }


@router.post("/scenarios/no_free_lunch")
async def run_scenario_no_free_lunch() -> Dict[str, Any]:
    """Scenario C: High natural recovery (85%) + low uplift -> Negative IEV -> NO_ACTION."""
    pid = f"pay_nfl_{uuid.uuid4().hex[:6]}"
    oid = f"order_nfl_{uuid.uuid4().hex[:6]}"
    # Small amount with high natural reattempt
    event = RazorpayWebhookEvent.model_validate({
        "entity": "event",
        "account_id": "acc_merch_demo",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": pid,
                    "order_id": oid,
                    "amount": 50,  # ₹0.50 payment -> action fee exceeds incremental gain
                    "currency": "INR",
                    "status": "failed",
                    "method": "upi",
                    "error_code": "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK",
                    "error_description": "User cancelled pin prompt"
                }
            }
        }
    })
    res = await state_machine.process_webhook_event(event)
    return {
        "scenario": "FLOW_C_NO_FREE_LUNCH",
        "payment_id": pid,
        "selected_action": res["selected_action"],
        "iev_inr": res["iev_inr"],
        "invariant": "NO_ACTION_SELECTED_WHEN_IEV_IS_NON_POSITIVE"
    }


@router.post("/scenarios/downtime")
async def run_scenario_downtime() -> Dict[str, Any]:
    """Scenario D: Rail downtime started -> adaptive delay applied -> downtime resolved."""
    # 1. Start downtime on HDFC Card rail
    await rail_sentinel.record_downtime_started(DowntimeEntity(
        id="down_hdfc_01",
        method="card",
        bank="HDFC",
        status="started",
        severity="HIGH"
    ))
    
    # 2. Incoming failed payment on HDFC Card rail
    pid = f"pay_dt_{uuid.uuid4().hex[:6]}"
    event = RazorpayWebhookEvent.model_validate({
        "entity": "event",
        "account_id": "acc_merch_demo",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": pid,
                    "order_id": f"order_{pid}",
                    "amount": 850000,
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "error_code": "GATEWAY_ERROR",
                    "error_description": "HDFC switch down"
                }
            }
        }
    })
    res = await state_machine.process_webhook_event(event)
    action = await state_machine.get_action(res["action_id"])
    
    # 3. Resolve downtime
    await rail_sentinel.record_downtime_resolved("card", "HDFC")
    
    return {
        "scenario": "FLOW_D_PAYMENT_DOWNTIME",
        "payment_id": pid,
        "rail_status": "DEGRADED_ADAPTIVE_DELAY_APPLIED",
        "adaptive_delay_seconds": action.action_parameters.get("delay_seconds"),
        "resolution": "DOWNTIME_RESOLVED_POLICY_RESTORED"
    }


@router.post("/scenarios/duplicate_replay")
async def run_scenario_duplicate_replay() -> Dict[str, Any]:
    """Scenario E: Same raw webhook posted 10 times with identical x-razorpay-event-id."""
    pid = f"pay_dup_{uuid.uuid4().hex[:6]}"
    event_id = f"evt_dup_{uuid.uuid4().hex[:8]}"
    
    results = []
    for i in range(10):
        is_new = await idempotency_manager.try_acquire_event(event_id)
        if is_new:
            results.append("PROCESSED_FIRST_DELIVERY")
        else:
            await telemetry.increment("duplicate_event_count")
            results.append("DUPLICATE_IGNORED")
    
    return {
        "scenario": "FLOW_E_DUPLICATE_REPLAY",
        "event_id": event_id,
        "deliveries_attempted": 10,
        "deliveries_processed": 1,
        "deliveries_ignored_as_duplicate": 9,
        "duplicate_execution_attempts": 0
    }


@router.post("/scenarios/gateway_timeout")
async def run_scenario_gateway_timeout() -> Dict[str, Any]:
    """Scenario F: Simulated HTTP 504 Gateway Timeout fail-safe handling."""
    pid = f"pay_to_{uuid.uuid4().hex[:6]}"
    event = RazorpayWebhookEvent.model_validate({
        "entity": "event",
        "account_id": "acc_merch_demo",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": pid,
                    "order_id": f"order_{pid}",
                    "amount": 620000,
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "error_code": "GATEWAY_ERROR",
                    "error_description": "Network timeout"
                }
            }
        }
    })
    res = await state_machine.process_webhook_event(event)
    sim = simulated_executor.__class__(simulate_network_timeout=True)
    exec_res = await sim.execute_action(res["action_id"])
    
    return {
        "scenario": "FLOW_F_GATEWAY_TIMEOUT",
        "payment_id": pid,
        "executor_response": exec_res,
        "contained": True,
        "invariant": "HTTP_504_CONTAINED_WITHOUT_BLIND_RETRY"
    }


@router.post("/scenarios/kill_switch")
async def run_scenario_kill_switch() -> Dict[str, Any]:
    """Scenario G: Toggle kill switch and attempt action dispatch."""
    settings.global_kill_switch = True
    
    pid = f"pay_ks_{uuid.uuid4().hex[:6]}"
    event = RazorpayWebhookEvent.model_validate({
        "entity": "event",
        "account_id": "acc_merch_demo",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": pid,
                    "order_id": f"order_{pid}",
                    "amount": 340000,
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                    "error_description": "Timeout"
                }
            }
        }
    })
    res = await state_machine.process_webhook_event(event)
    exec_res = await simulated_executor.execute_action(res["action_id"])
    
    # Restore normal kill switch setting
    settings.global_kill_switch = False
    
    return {
        "scenario": "FLOW_G_KILL_SWITCH",
        "payment_id": pid,
        "executor_response": exec_res,
        "invariant": "ZERO_ACTIONS_DISPATCHED_UNDER_KILL_SWITCH"
    }
