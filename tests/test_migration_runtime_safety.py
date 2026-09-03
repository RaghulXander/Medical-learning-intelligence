from unittest.mock import Mock, call

import pytest

from migrations.runtime_safety import ensure_postgresql_migrations_are_writable


def _connection(dialect_name: str, resulting_state: str = "off"):
    connection = Mock()
    connection.dialect.name = dialect_name
    set_result = Mock()
    show_result = Mock()
    show_result.scalar_one.return_value = resulting_state
    connection.exec_driver_sql.side_effect = [set_result, show_result]
    return connection


def test_postgresql_pool_state_is_reset_before_migration_transaction():
    connection = _connection("postgresql")

    ensure_postgresql_migrations_are_writable(connection)

    assert connection.exec_driver_sql.call_args_list == [
        call("SET default_transaction_read_only = off"),
        call("SHOW transaction_read_only"),
    ]
    connection.commit.assert_called_once_with()
    connection.rollback.assert_called_once_with()


def test_genuine_read_only_postgresql_connection_fails_with_clear_error():
    connection = _connection("postgresql", resulting_state="on")

    with pytest.raises(RuntimeError, match="writable PostgreSQL primary"):
        ensure_postgresql_migrations_are_writable(connection)


def test_non_postgresql_migrations_are_unchanged():
    connection = _connection("sqlite")

    ensure_postgresql_migrations_are_writable(connection)

    connection.exec_driver_sql.assert_not_called()
