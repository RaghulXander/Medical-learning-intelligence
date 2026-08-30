"""
backend/api/main.py

Main FastAPI application for Medical Exam AI.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database.db import get_engine

from backend.core.config import get_settings

from backend.api.routes.assessments import router as assessments_router
from backend.api.routes.questions import router as questions_router
from backend.api.routes.auth import router as auth_router
from backend.api.routes.student import router as student_router
from backend.api.routes.admin import router as admin_router
from backend.api.routes.cms import router as cms_router
from backend.api.routes.mobile_ui import router as mobile_ui_router

settings = get_settings()

app = FastAPI(
    title="Medical Exam AI — Core Assessment & Question Bank API",
    description="Universal Assessment Engine and Question Bank API for Medical Trainees.",
    version="1.0.0",
    docs_url=None if settings.is_production_like else "/docs",
    redoc_url=None if settings.is_production_like else "/redoc",
    openapi_url=None if settings.is_production_like else "/openapi.json",
)

# CORS middleware for Next.js / React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth_router)
app.include_router(student_router)
app.include_router(admin_router)
app.include_router(assessments_router)
app.include_router(questions_router)
app.include_router(cms_router)
app.include_router(mobile_ui_router)


@app.get("/api/health", include_in_schema=False)
def health_check():
    """Process liveness check; does not contact downstream services."""
    return {"status": "healthy", "service": "medical-exam-ai-backend"}


@app.get("/api/ready", include_in_schema=False)
def readiness_check():
    """Verify dependencies required to safely receive application traffic."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))

        if settings.redis_url:
            from redis import Redis

            client = Redis.from_url(
                settings.redis_url,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            try:
                client.ping()
            finally:
                client.close()
    except Exception:
        # Log collectors receive the exception from the server; the public
        # response deliberately avoids exposing connection details.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service dependencies are unavailable",
        )

    return {"status": "ready", "service": "medical-exam-ai-backend"}


@app.get("/api/version", include_in_schema=False)
def version_check():
    """Expose non-secret release identity for deployment verification."""
    return {
        "service": "medical-exam-ai-backend",
        "version": app.version,
        "release": settings.release_sha,
        "environment": settings.app_env,
    }
