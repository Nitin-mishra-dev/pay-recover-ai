"""FastAPI Application Factory."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.api.benchmark import router as benchmark_router
from src.api.cases import router as cases_router
from src.api.demo import router as demo_router
from src.api.safety import router as safety_router
from src.api.webhooks import router as webhooks_router
from src.core.audit import audit_ledger
from src.core.telemetry import telemetry


def create_app() -> FastAPI:
    app = FastAPI(
        title="PayRecover AI",
        description="Adaptive Post-Failure Revenue Recovery Decision Engine",
        version="0.1.0"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount domain routers
    app.include_router(webhooks_router)
    app.include_router(cases_router)
    app.include_router(demo_router)
    app.include_router(benchmark_router)
    app.include_router(safety_router)
    
    @app.get("/health", tags=["System"])
    async def health():
        return {"status": "ok", "service": "PayRecover AI"}
    
    @app.get("/telemetry", tags=["Observability"])
    async def get_telemetry():
        return await telemetry.snapshot()
    
    @app.get("/api/v1/audit/events", tags=["Audit"])
    async def get_audit_events():
        chain = await audit_ledger.get_chain()
        return [b.model_dump() for b in chain]
    
    @app.get("/audit/verify", tags=["Audit"])
    async def verify_audit_chain():
        return await audit_ledger.verify_chain()
    
    # Mount Static Files for UI if built
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    
    return app


app = create_app()
