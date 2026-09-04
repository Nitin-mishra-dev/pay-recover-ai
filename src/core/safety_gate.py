"""8-Stage Deterministic Safety Gate Kernel."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from pydantic import ValidationError
from src.config import settings
from src.core.audit import AuditEventType, audit_ledger
from src.core.idempotency import idempotency_manager
from src.core.state_machine import state_machine
from src.core.telemetry import telemetry
from src.models.actions import ActionType
from src.models.policy_decision import PolicyDecisionPayload
from src.models.state import ActionStatus, PaymentCase, PaymentState, RecoveryActionRecord


class SafetyGateResult:
    def __init__(self, authorized: bool, reason: str, action: Optional[RecoveryActionRecord] = None):
        self.authorized = authorized
        self.reason = reason
        self.action = action


class DeterministicSafetyKernel:
    """Enforces the 8-stage deterministic safety gate prior to external execution."""
    
    async def validate_and_authorize(
        self,
        action_id: str,
        raw_decision_dict: Optional[Dict[str, Any]] = None
    ) -> SafetyGateResult:
        """Runs all 8 deterministic verification stages on the candidate action."""
        
        # -------------------------------------------------------------
        # STAGE 1: Schema Validation (if raw reasoner JSON passed)
        # -------------------------------------------------------------
        if raw_decision_dict is not None:
            try:
                # Validates schema rigorously
                PolicyDecisionPayload.model_validate(raw_decision_dict)
            except (ValidationError, Exception) as e:
                await telemetry.increment("policy_validation_failure_count")
                await audit_ledger.record_event(
                    AuditEventType.SAFETY_CHECK_FAILED,
                    {"stage": 1, "error": "malformed_schema_fail_closed", "details": str(e)}
                )
                return SafetyGateResult(authorized=False, reason=f"STAGE_1_SCHEMA_INVALID: {str(e)}")
        
        # Fetch the canonical action record
        action = await state_machine.get_action(action_id)
        if not action:
            return SafetyGateResult(authorized=False, reason="ACTION_NOT_FOUND")
        
        case = await state_machine.get_case(action.case_id)
        if not case:
            return SafetyGateResult(authorized=False, reason="CASE_NOT_FOUND")
        
        # -------------------------------------------------------------
        # STAGE 2: Parameter Bounds Verification (Fail-Closed)
        # -------------------------------------------------------------
        if action.action_type == ActionType.RETRY_PAYMENT.value:
            delay = action.action_parameters.get("delay_seconds", 0)
            if not isinstance(delay, (int, float)) or delay < 0 or delay > 86400:
                await telemetry.increment("unauthorized_action_count")
                await audit_ledger.record_event(
                    AuditEventType.SAFETY_CHECK_FAILED,
                    {"stage": 2, "error": "invalid_delay_bounds", "delay_seconds": delay, "case_id": case.case_id},
                    case_id=case.case_id,
                    payment_id=case.payment_id
                )
                return SafetyGateResult(authorized=False, reason="STAGE_2_INVALID_DELAY_BOUNDS", action=action)
        elif action.action_type == ActionType.NOTIFY_PAYMENT_LINK.value:
            expiry = action.action_parameters.get("link_expiry_minutes", 1440)
            if not isinstance(expiry, (int, float)) or expiry < 5 or expiry > 10080:
                await telemetry.increment("unauthorized_action_count")
                await audit_ledger.record_event(
                    AuditEventType.SAFETY_CHECK_FAILED,
                    {"stage": 2, "error": "invalid_expiry_bounds", "link_expiry_minutes": expiry, "case_id": case.case_id},
                    case_id=case.case_id,
                    payment_id=case.payment_id
                )
                return SafetyGateResult(authorized=False, reason="STAGE_2_INVALID_EXPIRY_BOUNDS", action=action)
        
        # -------------------------------------------------------------
        # STAGE 3: Merchant Policy Compliance (Cooldowns)
        # -------------------------------------------------------------
        if action.action_type == ActionType.NOTIFY_PAYMENT_LINK.value:
            if case.notification_count >= 2:
                await telemetry.increment("unauthorized_action_count")
                await audit_ledger.record_event(
                    AuditEventType.SAFETY_CHECK_FAILED,
                    {"stage": 3, "error": "notification_frequency_cap_reached", "case_id": case.case_id},
                    case_id=case.case_id,
                    payment_id=case.payment_id
                )
                return SafetyGateResult(authorized=False, reason="STAGE_3_NOTIFICATION_CAP_REACHED", action=action)
        
        # -------------------------------------------------------------
        # STAGE 4: Safety Ceiling Checks (Attempts <= max)
        # -------------------------------------------------------------
        if action.action_type == ActionType.RETRY_PAYMENT.value:
            if case.attempt_count >= settings.max_retries_ceiling:
                await telemetry.increment("unauthorized_action_count")
                await audit_ledger.record_event(
                    AuditEventType.SAFETY_CHECK_FAILED,
                    {"stage": 4, "error": "retry_ceiling_reached", "attempt_count": case.attempt_count},
                    case_id=case.case_id,
                    payment_id=case.payment_id
                )
                await state_machine.update_case_state(case.case_id, PaymentState.STOPPED)
                return SafetyGateResult(authorized=False, reason="STAGE_4_RETRY_CEILING_REACHED", action=action)
        
        # -------------------------------------------------------------
        # STAGE 5: Transactional Payment State Freshness Check
        # -------------------------------------------------------------
        # Invariant: Payment MUST be in an open failure state. If already CAPTURED/REFUNDED, abort! (SS-02)
        if case.state in [PaymentState.CAPTURED, PaymentState.REFUNDED, PaymentState.DISPUTED]:
            await telemetry.increment("stale_action_rejection_count")
            await audit_ledger.record_event(
                AuditEventType.STALE_ACTION_CANCELLED,
                {"stage": 5, "error": "payment_state_not_failed", "current_state": case.state.value},
                case_id=case.case_id,
                payment_id=case.payment_id
            )
            await state_machine.update_action_status(action.action_id, ActionStatus.CANCELLED_STALE)
            return SafetyGateResult(authorized=False, reason=f"STAGE_5_STALE_PAYMENT_STATE_{case.state.value}", action=action)
        
        if action.status == ActionStatus.CANCELLED_STALE:
            await telemetry.increment("stale_action_rejection_count")
            return SafetyGateResult(authorized=False, reason="STAGE_5_ACTION_ALREADY_CANCELLED", action=action)
        
        # -------------------------------------------------------------
        # STAGE 6: Global Emergency Kill Switch
        # -------------------------------------------------------------
        # Invariant: Checked before lock acquisition to avoid burning idempotency leases during platform emergency stop
        if settings.global_kill_switch:
            await telemetry.increment("kill_switch_rejection_count")
            await audit_ledger.record_event(
                AuditEventType.KILL_SWITCH_BLOCKED,
                {"stage": 6, "note": "global_kill_switch_active", "action_id": action.action_id},
                case_id=case.case_id,
                payment_id=case.payment_id
            )
            await state_machine.update_action_status(action.action_id, ActionStatus.BLOCKED_KILL_SWITCH)
            return SafetyGateResult(authorized=False, reason="STAGE_6_GLOBAL_KILL_SWITCH_ACTIVE", action=action)
        
        # -------------------------------------------------------------
        # STAGE 7: Atomic Idempotency Lock Acquisition
        # -------------------------------------------------------------
        lock_acquired = await idempotency_manager.try_acquire_action_lock(action.idempotency_key)
        if not lock_acquired:
            await telemetry.increment("duplicate_execution_attempt_count")
            await audit_ledger.record_event(
                AuditEventType.SAFETY_CHECK_FAILED,
                {"stage": 7, "error": "action_idempotency_lock_conflict", "key": action.idempotency_key},
                case_id=case.case_id,
                payment_id=case.payment_id
            )
            return SafetyGateResult(authorized=False, reason="STAGE_7_IDEMPOTENCY_CONFLICT", action=action)
        
        # -------------------------------------------------------------
        # STAGE 8: Execution Authorization
        # -------------------------------------------------------------
        await state_machine.update_action_status(action.action_id, ActionStatus.AUTHORIZED)
        await audit_ledger.record_event(
            AuditEventType.SAFETY_CHECK_PASSED,
            {"stage": 8, "action_id": action.action_id, "action_type": action.action_type},
            case_id=case.case_id,
            payment_id=case.payment_id
        )
        return SafetyGateResult(authorized=True, reason="AUTHORIZED", action=action)


safety_kernel = DeterministicSafetyKernel()
