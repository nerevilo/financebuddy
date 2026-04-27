"""
Ledgi API - Personal Finance Tracking Application

FastAPI backend for tracking spending across multiple financial institutions.
"""
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from .core.config import get_settings
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
    chat_router,
    api_keys_router,
    llm_api_router,
)

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
    title="Ledgi API",
    description="Personal finance tracking API with Teller integration",
    version="0.1.0"
)

# Add rate limiter to app state and register exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", extra={"path": request.url.path, "error": str(exc)})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Request-ID"] = str(uuid.uuid4())
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        latency_ms = round((time.monotonic() - start) * 1000)
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response


# Middleware is applied in reverse order — logging outermost, security headers innermost
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",  # Next.js dev server (fallback port)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://olivefinance.vercel.app",  # Production alias
    ],
    allow_origin_regex=r"^https://[a-z0-9-]+-renjialans-projects\.vercel\.app$",  # All Vercel preview URLs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-API-Key"],
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
app.include_router(api_keys_router)
app.include_router(llm_api_router)

# Mount MCP server for AI client access (Claude Desktop, Claude Code, Cursor, etc.)
from .mcp_server.server import mcp as mcp_server

mcp_app = mcp_server.http_app(path="/", stateless_http=True)
app.mount("/mcp", mcp_app)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Ledgi API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check."""
    return {"status": "healthy"}
