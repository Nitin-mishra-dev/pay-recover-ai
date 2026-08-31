"""Authoritative Payment State Machine with transactional updates and push-cancellation."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.config import settings
from src.core.audit import AuditEventType, audit_ledger
from src.core.downtime import rail_sentinel
from src.core.economics import economic_engine
from src.core.idempotency import idempotency_manager
from src.core.telemetry import telemetry
from src.models.actions import ActionType
from src.models.events import RazorpayEventType, RazorpayWebhookEvent
from src.models.state import ActionStatus, PaymentCase, PaymentState, RecoveryActionRecord


class PaymentStateMachine:
    """Authoritative aggregate state store and transition engine."""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        self._cases_by_id: Dict[str, PaymentCase] = {}
        self._cases_by_payment: Dict[str, str] = {}  # payment_id -> case_id
        self._cases_by_order: Dict[str, List[str]] = {}  # order_id -> list of case_ids
        self._actions_by_id: Dict[str, RecoveryActionRecord] = {}
    
    async def process_webhook_event(self, event: RazorpayWebhookEvent) -> Dict[str, Any]:
        """Processes an incoming validated Razorpay webhook and updates state authoritatively."""
        async with self._lock:
            event_type = event.event
            
            # 1. Handle Downtime Events
            if event_type == RazorpayEventType.DOWNTIME_STARTED:
                dt_data = event.payload.downtime or {}
                method = dt_data.get("method", "all")
                bank = dt_data.get("bank")
                network = dt_data.get("network")
                await audit_ledger.record_event(
                    AuditEventType.DOWNTIME_STARTED,
                    {"method": method, "bank": bank, "network": network, "payload": dt_data}
                )
                return {"status": "downtime_recorded"}
            
            elif event_type == RazorpayEventType.DOWNTIME_RESOLVED:
                dt_data = event.payload.downtime or {}
                method = dt_data.get("method", "all")
                bank = dt_data.get("bank")
                network = dt_data.get("network")
                await rail_sentinel.record_downtime_resolved(method, bank, network)
                await audit_ledger.record_event(
                    AuditEventType.DOWNTIME_RESOLVED,
                    {"method": method, "bank": bank, "network": network}
                )
                return {"status": "downtime_resolved"}
            
            # 2. Extract payment entity
            payment_data = event.payload.payment
            if not payment_data:
                return {"status": "no_payment_payload"}
            
            payment_entity = payment_data.get("entity", payment_data)
            payment_id = payment_entity.get("id")
            order_id = payment_entity.get("order_id", f"order_synth_{payment_id}")
            amount = payment_entity.get("amount", 0)
            
            # 3. Handle PAYMENT_CAPTURED / SUCCESS
            if event_type == RazorpayEventType.PAYMENT_CAPTURED or event_type == RazorpayEventType.PAYMENT_AUTHORIZED:
                case_id = self._cases_by_payment.get(payment_id)
                case = self._cases_by_id.get(case_id) if case_id else None
                
                if not case:
                    # Initialize captured case if not previously failed
                    case_id = f"case_{uuid.uuid4().hex[:12]}"
                    case = PaymentCase(
                        case_id=case_id,
                        payment_id=payment_id,
                        order_id=order_id,
                        amount_paise=amount,
                        state=PaymentState.CAPTURED,
                        payment_method=payment_entity.get("method", "card")
                    )
                    self._cases_by_id[case_id] = case
                    self._cases_by_payment[payment_id] = case_id
                    self._cases_by_order.setdefault(order_id, []).append(case_id)
                else:
                    case.state = PaymentState.CAPTURED
                    case.updated_at = datetime.now(timezone.utc)
                
                # PUSH CANCELLATION: Cancel any in-flight scheduled actions for this order/payment
                await self._cancel_scheduled_actions_for_order_locked(order_id, payment_id, reason="payment_captured")
                
                await audit_ledger.record_event(
                    AuditEventType.PAYMENT_CAPTURED_OBSERVED,
                    {"payment_id": payment_id, "order_id": order_id, "amount": amount},
                    case_id=case.case_id,
                    payment_id=payment_id
                )
                return {"status": "captured_processed", "case_id": case.case_id}
            
            # 4. Handle PAYMENT_FAILED
            elif event_type == RazorpayEventType.PAYMENT_FAILED:
                case_id = self._cases_by_payment.get(payment_id)
                case = self._cases_by_id.get(case_id) if case_id else None
                
                # Invariant: If state is already CAPTURED (out-of-order failure), discard! (SS-04)
                if case and case.state == PaymentState.CAPTURED:
                    await audit_ledger.record_event(
                        AuditEventType.WEBHOOK_RECEIVED,
                        {"note": "out_of_order_failure_after_capture_ignored", "payment_id": payment_id},
                        case_id=case.case_id,
                        payment_id=payment_id
                    )
                    return {"status": "out_of_order_ignored", "state": case.state}
                
                if not case:
                    case_id = f"case_{uuid.uuid4().hex[:12]}"
                    case = PaymentCase(
                        case_id=case_id,
                        payment_id=payment_id,
                        order_id=order_id,
                        amount_paise=amount,
                        state=PaymentState.OBSERVED_FAILED,
                        payment_method=payment_entity.get("method", "card"),
                        error_code=payment_entity.get("error_code"),
                        error_description=payment_entity.get("error_description"),
                        customer_email=payment_entity.get("email"),
                        customer_contact=payment_entity.get("contact"),
                        attempt_count=0
                    )
                    self._cases_by_id[case_id] = case
                    self._cases_by_payment[payment_id] = case_id
                    self._cases_by_order.setdefault(order_id, []).append(case_id)
                else:
                    case.state = PaymentState.OBSERVED_FAILED
                    case.error_code = payment_entity.get("error_code", case.error_code)
                    case.error_description = payment_entity.get("error_description", case.error_description)
                    case.updated_at = datetime.now(timezone.utc)
                
                await audit_ledger.record_event(
                    AuditEventType.PAYMENT_FAILED_OBSERVED,
                    {
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "amount_paise": amount,
                        "error_code": case.error_code,
                        "error_description": case.error_description
                    },
                    case_id=case.case_id,
                    payment_id=payment_id
                )
                
                # Check degradation and generate candidates
                is_degraded = await rail_sentinel.is_rail_degraded(case.payment_method)
                adaptive_delay = await rail_sentinel.get_adaptive_delay(case.payment_method)
                
                candidates = economic_engine.generate_and_score_candidates(
                    case=case,
                    is_degraded=is_degraded,
                    adaptive_delay=adaptive_delay
                )
                best_action = economic_engine.select_best_action(candidates)
                
                # Compute internal action idempotency key
                idempotency_key = idempotency_manager.compute_action_idempotency_key(
                    merchant_id=case.merchant_id,
                    payment_id=case.payment_id,
                    action_type=best_action.action_type.value,
                    action_parameters=best_action.parameters,
                    decision_version="v1"
                )
                
                action_record = RecoveryActionRecord(
                    action_id=f"act_{uuid.uuid4().hex[:12]}",
                    case_id=case.case_id,
                    payment_id=case.payment_id,
                    order_id=case.order_id,
                    merchant_id=case.merchant_id,
                    action_type=best_action.action_type.value,
                    action_parameters=best_action.parameters,
                    idempotency_key=idempotency_key,
                    status=ActionStatus.PROPOSED,
                    expected_incremental_value=best_action.expected_incremental_value_inr
                )
                
                self._actions_by_id[action_record.action_id] = action_record
                case.active_action_id = action_record.action_id
                case.state = PaymentState.DECISION_READY
                
                await audit_ledger.record_event(
                    AuditEventType.DECISION_EVALUATED,
                    {
                        "action_id": action_record.action_id,
                        "selected_action": best_action.action_type.value,
                        "parameters": best_action.parameters,
                        "iev_inr": best_action.expected_incremental_value_inr,
                        "all_candidates": [c.model_dump() for c in candidates]
                    },
                    case_id=case.case_id,
                    payment_id=payment_id
                )
                
                return {
                    "status": "failed_evaluated",
                    "case_id": case.case_id,
                    "action_id": action_record.action_id,
                    "selected_action": best_action.action_type.value,
                    "iev_inr": best_action.expected_incremental_value_inr
                }
            
            # 5. Handle Refund / Dispute Events
            elif event_type in [RazorpayEventType.REFUND_CREATED, RazorpayEventType.DISPUTE_CREATED]:
                case_id = self._cases_by_payment.get(payment_id)
                if case_id and case_id in self._cases_by_id:
                    case = self._cases_by_id[case_id]
                    case.state = PaymentState.DISPUTED if event_type == RazorpayEventType.DISPUTE_CREATED else PaymentState.REFUNDED
                    await self._cancel_scheduled_actions_for_order_locked(order_id, payment_id, reason="dispute_or_refund")
                return {"status": "hold_recorded"}
            
            return {"status": "event_unhandled"}
    
    async def _cancel_scheduled_actions_for_order_locked(self, order_id: str, payment_id: str, reason: str) -> None:
        """Push-cancellation of pending scheduled actions for this order/payment."""
        for act in self._actions_by_id.values():
            if (act.order_id == order_id or act.payment_id == payment_id) and act.status in [ActionStatus.PROPOSED, ActionStatus.SCHEDULED]:
                act.status = ActionStatus.CANCELLED_STALE
                await telemetry.increment("stale_action_rejection_count")
                await audit_ledger.record_event(
                    AuditEventType.STALE_ACTION_CANCELLED,
                    {"action_id": act.action_id, "payment_id": act.payment_id, "reason": reason},
                    case_id=act.case_id,
                    payment_id=act.payment_id
                )
    
    async def get_case(self, case_id: str) -> Optional[PaymentCase]:
        async with self._lock:
            return self._cases_by_id.get(case_id)
    
    async def get_case_by_payment(self, payment_id: str) -> Optional[PaymentCase]:
        async with self._lock:
            case_id = self._cases_by_payment.get(payment_id)
            return self._cases_by_id.get(case_id) if case_id else None
    
    async def get_action(self, action_id: str) -> Optional[RecoveryActionRecord]:
        async with self._lock:
            return self._actions_by_id.get(action_id)
    
    async def update_case_state(self, case_id: str, new_state: PaymentState) -> None:
        async with self._lock:
            if case_id in self._cases_by_id:
                self._cases_by_id[case_id].state = new_state
                self._cases_by_id[case_id].updated_at = datetime.now(timezone.utc)
    
    async def update_action_status(self, action_id: str, new_status: ActionStatus, outcome: Optional[str] = None) -> None:
        async with self._lock:
            if action_id in self._actions_by_id:
                act = self._actions_by_id[action_id]
                act.status = new_status
                if outcome:
                    act.outcome = outcome
                if new_status in [ActionStatus.SUCCEEDED, ActionStatus.FAILED]:
                    act.executed_at = datetime.now(timezone.utc)
    
    async def reset(self) -> None:
        async with self._lock:
            self._cases_by_id.clear()
            self._cases_by_payment.clear()
            self._cases_by_order.clear()
            self._actions_by_id.clear()


# Global singleton instance
state_machine = PaymentStateMachine()
