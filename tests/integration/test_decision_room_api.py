"""Integration tests for Decision Room and Failure Lab APIs."""

import pytest
from httpx import ASGITransport, AsyncClient
from src.api.app import create_app


@pytest.mark.asyncio
async def test_decision_room_flow_and_scenarios():
    """Tests complete Decision Room, Case Execution, and Failure Lab scenarios."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Reset demo state
        reset_res = await client.post("/api/v1/demo/reset")
        assert reset_res.status_code == 200
        assert reset_res.json()["cases_initialized"] == 5
        
        # 2. List cases
        cases_res = await client.get("/api/v1/cases")
        assert cases_res.status_code == 200
        cases = cases_res.json()
        assert len(cases) == 5
        
        # 3. Get details for first case
        case_id = cases[0]["case_id"]
        detail_res = await client.get(f"/api/v1/cases/{case_id}")
        assert detail_res.status_code == 200
        details = detail_res.json()
        assert "candidate_actions" in details
        assert len(details["candidate_actions"]) > 0
        assert details["safety_checks"]["idempotency_lock_valid"] is True
        
        # 4. Execute action for first case
        exec_res = await client.post(f"/api/v1/cases/{case_id}/execute", json={})
        assert exec_res.status_code == 200
        assert exec_res.json()["success"] is True
        
        # 5. Test Failure Lab Flow B: Capture Race Interception
        race_res = await client.post("/api/v1/demo/scenarios/capture_race")
        assert race_res.status_code == 200
        race_data = race_res.json()
        assert race_data["invariant"] == "STALE_RETRY_INTERCEPTED_AND_CANCELLED"
        assert race_data["duplicate_executions"] == 0
        
        # 6. Test Failure Lab Flow C: No Free Lunch
        nfl_res = await client.post("/api/v1/demo/scenarios/no_free_lunch")
        assert nfl_res.status_code == 200
        nfl_data = nfl_res.json()
        assert nfl_data["selected_action"] == "no_action"
        
        # 7. Test Failure Lab Flow D: Payment Downtime
        dt_res = await client.post("/api/v1/demo/scenarios/downtime")
        assert dt_res.status_code == 200
        dt_data = dt_res.json()
        assert dt_data["adaptive_delay_seconds"] >= 1800
        
        # 8. Test Failure Lab Flow E: Duplicate Replay
        dup_res = await client.post("/api/v1/demo/scenarios/duplicate_replay")
        assert dup_res.status_code == 200
        dup_data = dup_res.json()
        assert dup_data["deliveries_processed"] == 1
        assert dup_data["deliveries_ignored_as_duplicate"] == 9
        
        # 9. Test Benchmark Summary Artifact Serving
        bench_res = await client.get("/api/v1/benchmark/summary")
        assert bench_res.status_code == 200
        bench_data = bench_res.json()
        assert bench_data["headline_metrics"]["niv_uplift_vs_static_rules_pct"] == 8.92
        
        # 10. Test Audit Hash Chain Verification
        audit_res = await client.get("/audit/verify")
        assert audit_res.status_code == 200
        audit_data = audit_res.json()
        assert audit_data["valid"] is True
        assert audit_data["blocks_audited"] > 0
