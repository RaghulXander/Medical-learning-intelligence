"""
backend/api/main.py

Main FastAPI application for Medical Exam AI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.assessments import router as assessments_router

app = FastAPI(
    title="Medical Exam AI — Core Assessment API",
    description="Universal Assessment Engine and Question Bank API for Medical Trainees.",
    version="1.0.0",
)

# CORS middleware for Next.js / React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(assessments_router)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "medical-exam-ai-backend"}
