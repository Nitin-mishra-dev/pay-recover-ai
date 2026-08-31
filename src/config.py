"""PayRecover AI Global Configuration & Environment Settings."""

import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings with environment variable fallbacks."""
    
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    database_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:"))
    razorpay_webhook_secret: str = Field(default_factory=lambda: os.getenv("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret_key_12345"))
    global_kill_switch: bool = Field(default_factory=lambda: os.getenv("GLOBAL_KILL_SWITCH", "false").lower() == "true")
    max_retries_ceiling: int = Field(default=3)
    notification_cooldown_seconds: int = Field(default=7200)  # 2 hours
    retry_cooldown_seconds: int = Field(default=300)  # 5 minutes
    
    # Economics parameters
    direct_retry_cost_inr: float = Field(default=0.50)
    sms_cost_inr: float = Field(default=0.20)
    email_cost_inr: float = Field(default=0.02)
    customer_annoyance_penalty_inr: float = Field(default=2.00)
    human_ops_cost_inr: float = Field(default=50.00)
    chargeback_loss_penalty_inr: float = Field(default=250.00)


settings = Settings()
