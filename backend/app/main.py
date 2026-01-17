"""
FinTrack API - Personal Finance Tracking Application

FastAPI backend for tracking spending across multiple financial institutions.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .core.config import get_settings
from .core.database import engine, Base
from .core.logging_config import setup_logging, get_logger
from .core.rate_limiter import limiter

# Initialize logging before anything else
setup_logging()
logger = get_logger(__name__)

from .routers import (
    auth_router,
    accounts_router,
    transactions_router,
    analytics_router,
    teller_router,
    categorization_router,
    dashboard_router,
    institutions_router,
    goals_router,
    income_router,
    insights_router,
    profile_router,
    anomalies_router,
    tags_router,
    chat_router
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
settings = get_settings()

# Security check: prevent running with debug=True in non-development environments
import os
if settings.debug and os.getenv("ENVIRONMENT", "development") != "development":
    raise RuntimeError(
        "Cannot run with debug=True outside of development environment. "
        "Set DEBUG=false in your .env file for non-development environments."
    )

app = FastAPI(
    title="FinTrack API",
    description="Personal finance tracking API with Teller integration",
    version="0.1.0"
)

# Add rate limiter to app state and register exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
        "https://olivefinance.vercel.app",  # Production alias
    ],
    allow_origin_regex=r"https://.*-renjialans-projects\.vercel\.app",  # All Vercel preview URLs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Include routers
app.include_router(auth_router)
app.include_router(teller_router)
app.include_router(accounts_router)
app.include_router(transactions_router)
app.include_router(analytics_router)
app.include_router(categorization_router)
app.include_router(dashboard_router)
app.include_router(institutions_router)
app.include_router(goals_router)
app.include_router(income_router)
app.include_router(insights_router)
app.include_router(profile_router)
app.include_router(anomalies_router)
app.include_router(tags_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "name": "FinTrack API",
        "version": "0.1.0",
        "status": "running",
        "teller_env": settings.teller_env
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "teller": {
            "app_id": settings.teller_app_id,
            "environment": settings.teller_env
        }
    }
