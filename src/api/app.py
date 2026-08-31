"""FastAPI Application Factory."""

from fastapi import FastAPI
from src.api.webhooks import router as webhooks_router
from src.core.audit import audit_ledger
from src.core.telemetry import telemetry


def create_app() -> FastAPI:
    app = FastAPI(
        title="PayRecover AI",
        description="Adaptive Post-Failure Revenue Recovery Decision Engine",
        version="0.1.0"
    )
    
    app.include_router(webhooks_router)
    
    @app.get("/health", tags=["System"])
    async def health():
        return {"status": "ok", "service": "PayRecover AI"}
    
    @app.get("/telemetry", tags=["Observability"])
    async def get_telemetry():
        return await telemetry.snapshot()
    
    @app.get("/audit/verify", tags=["Audit"])
    async def verify_audit_chain():
        return await audit_ledger.verify_chain()
    
    return app


app = create_app()
