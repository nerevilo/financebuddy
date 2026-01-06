"""
FinTrack API - Personal Finance Tracking Application

FastAPI backend for tracking spending across multiple financial institutions.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.database import engine, Base
from .routers import accounts_router, transactions_router, analytics_router, teller_router

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
settings = get_settings()

app = FastAPI(
    title="FinTrack API",
    description="Personal finance tracking API with Teller integration",
    version="0.1.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(teller_router)
app.include_router(accounts_router)
app.include_router(transactions_router)
app.include_router(analytics_router)


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
