"""Regression tests for the shared FastAPI database dependency."""

from unittest.mock import Mock, patch

from backend.api.routes.auth import get_db


def test_get_db_uses_cached_session_factory_and_closes_session():
    session = Mock()
    factory = Mock(return_value=session)

    with patch("backend.api.routes.auth.get_session_factory", return_value=factory) as getter:
        dependency = get_db()
        assert next(dependency) is session

        try:
            next(dependency)
        except StopIteration:
            pass

    getter.assert_called_once_with()
    factory.assert_called_once_with()
    session.close.assert_called_once_with()
