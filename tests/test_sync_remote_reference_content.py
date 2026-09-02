from pathlib import Path

import pytest

from scripts.sync_remote_reference_content import DEFAULT_DOCUMENTS, _load_remote_url


def test_three_book_sync_is_the_default():
    assert DEFAULT_DOCUMENTS == (
        "robbins_review",
        "robbins_pathologic_basis_11th",
        "sternberg_review_2nd",
    )


def test_remote_url_prefers_dedicated_key(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://user:pass@localhost/local\n"
        "REMOTE_DATABASE_URL=postgresql://user:pass@remote.example/remote\n",
        encoding="utf-8",
    )
    assert _load_remote_url(env_file) == "postgresql://user:pass@remote.example/remote"


def test_remote_url_refuses_localhost(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://user:pass@localhost/local\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="refuses a localhost URL"):
        _load_remote_url(env_file)
