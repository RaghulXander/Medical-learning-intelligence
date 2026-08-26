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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    default_origins = "http://localhost:3000,http://127.0.0.1:3000"
    settings = Settings(
        app_env=app_env,
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", DEVELOPMENT_JWT_SECRET),
        google_client_ids=_csv(
            os.getenv("GOOGLE_CLIENT_IDS", os.getenv("GOOGLE_CLIENT_ID", ""))
        ),
        cors_allowed_origins=_csv(os.getenv("CORS_ALLOWED_ORIGINS", default_origins)),
        redis_url=os.getenv("REDIS_URL", "").strip(),
        release_sha=os.getenv("RELEASE_SHA", os.getenv("COMMIT_SHA", "development")).strip(),
    )
    settings.validate()
    return settings


def reset_settings_cache() -> None:
    """Clear cached settings. Intended for tests that modify the environment."""
    get_settings.cache_clear()
