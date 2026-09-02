"""
tests/test_diagnostics_sanitization.py

Unit tests for Milestone 17 Diagnostics & Sanitization:
- Automatic token, password, and email redaction
- Crash report ingestion endpoint validation
"""

import pytest
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.api.routes.diagnostics import sanitize_diagnostic_text


def test_sanitize_diagnostic_text():
    """Verifies that sensitive credentials, tokens, and emails are strictly redacted."""
    raw_stack = (
        "Error: Request failed with status 401\n"
        "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisToken\n"
        "User email: doctor.john@hospital.org\n"
        "Payload: { password: \"superSecretPass123!\" }"
    )

    cleaned = sanitize_diagnostic_text(raw_stack)

    assert "doNotLeakThisToken" not in cleaned
    assert "doctor.john@hospital.org" not in cleaned
    assert "superSecretPass123!" not in cleaned
    assert "[REDACTED_TOKEN]" in cleaned
    assert "[REDACTED_EMAIL]" in cleaned
    assert "password:[REDACTED]" in cleaned


def test_submit_crash_report_endpoint():
    """Verifies POST /api/diagnostics/crash-report accepts and records reports."""
    client = TestClient(app)

    payload = {
        "app_version": "1.0.1",
        "runtime_version": "1.0.1",
        "git_tag": "android-beta-v1.0.1",
        "os_name": "Android",
        "os_version": "14",
        "device_model": "Pixel 8 Pro",
        "category": "NETWORK_TIMEOUT",
        "error_message": "Timeout connecting to API with Bearer eyJhbGciOiJIUzI1Ni.someTokenHere.xyz",
        "stack_trace": "NetworkError at fetch (native)\n    at Object.request (client.ts:42)",
        "metadata": {"screen": "exam/[attemptId]", "attempt_id": "test-attempt-123"},
    }

    response = client.post("/api/diagnostics/crash-report", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "report_id" in data
    assert data["status"] == "RECORDED"
