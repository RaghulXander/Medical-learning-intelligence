"""Server-only GitHub Contents API adapter for CMS publications."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


class CmsNotConfigured(RuntimeError):
    pass


class CmsPublishConflict(RuntimeError):
    pass


class CmsPublishError(RuntimeError):
    pass


@dataclass(frozen=True)
class CmsGitHubSettings:
    owner: str
    repository: str
    branch: str
    content_path: str
    token: str

    @classmethod
    def from_environment(cls) -> "CmsGitHubSettings":
        return cls(
            owner=os.getenv("CMS_GITHUB_OWNER", "RaghulXander").strip(),
            repository=os.getenv("CMS_GITHUB_REPOSITORY", "Medical-learning-intelligence").strip(),
            branch=os.getenv("CMS_GITHUB_BRANCH", "main").strip(),
            content_path=os.getenv("CMS_GITHUB_CONTENT_PATH", "apps/web/content/landing-page.json").strip(),
            token=os.getenv("CMS_GITHUB_TOKEN", "").strip(),
        )

    @property
    def configured(self) -> bool:
        return bool(self.owner and self.repository and self.branch and self.content_path and self.token)


class GitHubContentPublisher:
    def __init__(self, settings: CmsGitHubSettings | None = None):
        self.settings = settings or CmsGitHubSettings.from_environment()

    def _headers(self) -> dict[str, str]:
        if not self.settings.configured:
            raise CmsNotConfigured("GitHub CMS publishing is not configured")
        return {
            "Authorization": f"Bearer {self.settings.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _contents_url(self) -> str:
        return (
            f"https://api.github.com/repos/{self.settings.owner}/"
            f"{self.settings.repository}/contents/{self.settings.content_path}"
        )

    def get_document(self, ref: str | None = None) -> tuple[dict[str, Any], str]:
        response = requests.get(
            self._contents_url(),
            headers=self._headers(),
            params={"ref": ref or self.settings.branch},
            timeout=15,
        )
        if not response.ok:
            raise CmsPublishError(f"GitHub content read failed with status {response.status_code}")
        payload = response.json()
        try:
            document = json.loads(base64.b64decode(payload["content"]).decode("utf-8"))
            return document, payload["sha"]
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise CmsPublishError("GitHub returned an invalid CMS content response") from exc

    def publish(self, document: dict[str, Any], base_sha: str | None, message: str) -> dict[str, Any]:
        _, current_sha = self.get_document()
        if base_sha and current_sha != base_sha:
            raise CmsPublishConflict("Landing-page content changed after this editor loaded it")
        encoded = base64.b64encode(
            (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        ).decode("ascii")
        response = requests.put(
            self._contents_url(),
            headers=self._headers(),
            json={
                "message": message,
                "content": encoded,
                "branch": self.settings.branch,
                "sha": current_sha,
            },
            timeout=20,
        )
        if response.status_code in {409, 422}:
            raise CmsPublishConflict("GitHub rejected the update because the content revision changed")
        if not response.ok:
            raise CmsPublishError(f"GitHub content update failed with status {response.status_code}")
        payload = response.json()
        return {
            "commit_sha": payload.get("commit", {}).get("sha"),
            "commit_url": payload.get("commit", {}).get("html_url"),
            "content_sha": payload.get("content", {}).get("sha"),
        }

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        url = f"https://api.github.com/repos/{self.settings.owner}/{self.settings.repository}/commits"
        response = requests.get(
            url,
            headers=self._headers(),
            params={"sha": self.settings.branch, "path": self.settings.content_path, "per_page": limit},
            timeout=15,
        )
        if not response.ok:
            raise CmsPublishError(f"GitHub history read failed with status {response.status_code}")
        return [
            {
                "sha": item.get("sha"),
                "url": item.get("html_url"),
                "message": item.get("commit", {}).get("message"),
                "created_at": item.get("commit", {}).get("author", {}).get("date"),
            }
            for item in response.json()
        ]


def read_local_document() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "apps" / "web" / "content" / "landing-page.json"
    return json.loads(path.read_text(encoding="utf-8"))
