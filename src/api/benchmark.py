"""FastAPI Benchmark Router - Serves Verified Multi-Seed & Multi-World Artifacts."""

import json
import os
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/api/v1/benchmark", tags=["Benchmark"])

RESULTS_DIR = "eval/results"


@router.get("/summary")
async def get_benchmark_summary() -> Dict[str, Any]:
    """Returns the primary multi-seed sealed holdout benchmark results."""
    primary_path = os.path.join(RESULTS_DIR, "benchmark_holdout_multiseed.json")
    if not os.path.exists(primary_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark artifacts not generated yet")
    with open(primary_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/ai-ab")
async def get_ai_ab_summary() -> Dict[str, Any]:
    """Returns the A/B AI evaluation experiment artifact."""
    ab_path = os.path.join(RESULTS_DIR, "ai_ab", "benchmark_ai_ab.json")
    if not os.path.exists(ab_path):
        return {"status": "pending_generation"}
    with open(ab_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/worlds")
async def get_multi_world_summary() -> Dict[str, Any]:
    """Returns comparative results across World V1, V2, and V3."""
    v1_path = os.path.join(RESULTS_DIR, "benchmark_holdout_multiseed.json")
    v2_path = os.path.join(RESULTS_DIR, "benchmark_holdout_v2_weak_retry_strong_notify_multiseed.json")
    
    data = {}
    if os.path.exists(v1_path):
        with open(v1_path, "r", encoding="utf-8") as f:
            data["v1_standard"] = json.load(f)["headline_metrics"]
    if os.path.exists(v2_path):
        with open(v2_path, "r", encoding="utf-8") as f:
            data["v2_weak_retry_strong_notify"] = json.load(f)["headline_metrics"]
            
    return data
