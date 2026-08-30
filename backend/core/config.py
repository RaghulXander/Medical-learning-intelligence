"""Typed application configuration and production safety validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Tuple


DEVELOPMENT_JWT_SECRET = "docedge_secret_jwt_key_development_only_2026_xander"
PRODUCTION_ENVIRONMENTS = {"production", "staging"}


def _csv(value: str) -> Tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_env: str
    jwt_secret_key: str
    google_client_ids: Tuple[str, ...]
    cors_allowed_origins: Tuple[str, ...]
    redis_url: str
    release_sha: str
    gcp_project_id: str = ""
    gcp_location: str = "us"
    gcp_processor_id: str = ""
    gcp_processor_version_id: str = ""
    gcp_raw_bucket: str = ""
    gcp_processed_bucket: str = ""
    docai_max_online_pages: int = 15
    docai_mock_fallback: bool = False

    @property
    def is_production_like(self) -> bool:
        return self.app_env in PRODUCTION_ENVIRONMENTS

    @property
    def allows_test_auth(self) -> bool:
        return self.app_env == "test"

    def validate(self) -> None:
        errors = []
        if self.is_production_like:
            if not self.jwt_secret_key or self.jwt_secret_key == DEVELOPMENT_JWT_SECRET:
                errors.append("JWT_SECRET_KEY must be set to a non-development secret")
            if not self.google_client_ids:
                errors.append("GOOGLE_CLIENT_IDS must contain at least one OAuth client ID")
            if not self.cors_allowed_origins:
                errors.append("CORS_ALLOWED_ORIGINS must contain at least one explicit origin")
            if "*" in self.cors_allowed_origins:
                errors.append("CORS_ALLOWED_ORIGINS cannot contain '*' in production or staging")
        if errors:
            raise RuntimeError("Invalid application configuration: " + "; ".join(errors))

    def validate_document_ai(self) -> None:
        """Fail before a live request when required Document AI settings are absent."""
        missing = []
        if not self.gcp_project_id:
            missing.append("GCP_PROJECT_ID")
        if not self.gcp_processor_id:
            missing.append("GCP_PROCESSOR_ID")
        if not self.gcp_processor_version_id:
            missing.append("GCP_PROCESSOR_VERSION_ID")
        if not 1 <= self.docai_max_online_pages <= 15:
            raise RuntimeError("DOCAI_MAX_ONLINE_PAGES must be between 1 and 15")
        if missing:
            raise RuntimeError(
                "Document AI is not configured; set " + ", ".join(missing)
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    default_origins = "http://localhost:3000,http://127.0.0.1:3000"
    mock_fallback = os.getenv("DOCAI_MOCK_FALLBACK", "false").strip().lower() in ("true", "1", "yes")
    try:
        max_online_pages = int(os.getenv("DOCAI_MAX_ONLINE_PAGES", "15"))
    except ValueError:
        max_online_pages = 15

    settings = Settings(
        app_env=app_env,
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", DEVELOPMENT_JWT_SECRET),
        google_client_ids=_csv(
            os.getenv("GOOGLE_CLIENT_IDS", os.getenv("GOOGLE_CLIENT_ID", ""))
        ),
        cors_allowed_origins=_csv(os.getenv("CORS_ALLOWED_ORIGINS", default_origins)),
        redis_url=os.getenv("REDIS_URL", "").strip(),
        release_sha=os.getenv(
            "RELEASE_SHA",
            os.getenv("RENDER_GIT_COMMIT", os.getenv("COMMIT_SHA", "development")),
        ).strip(),
        gcp_project_id=os.getenv("GCP_PROJECT_ID", "").strip(),
        gcp_location=os.getenv("GCP_LOCATION", "us").strip(),
        gcp_processor_id=os.getenv("GCP_PROCESSOR_ID", "").strip(),
        gcp_processor_version_id=os.getenv("GCP_PROCESSOR_VERSION_ID", "").strip(),
        gcp_raw_bucket=os.getenv("GCP_RAW_BUCKET", "").strip(),
        gcp_processed_bucket=os.getenv("GCP_PROCESSED_BUCKET", "").strip(),
        docai_max_online_pages=max_online_pages,
        docai_mock_fallback=mock_fallback,
    )
    settings.validate()
    return settings


def reset_settings_cache() -> None:
    """Clear cached settings. Intended for tests that modify the environment."""
    get_settings.cache_clear()
