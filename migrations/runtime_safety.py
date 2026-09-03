"""Safety checks used before Alembic opens its migration transaction."""


def ensure_postgresql_migrations_are_writable(connection) -> None:
    """Clear leaked pooled-session read-only state and verify the next transaction.

    Session-level PostgreSQL settings can survive client disconnects behind a
    connection pooler. Alembic migrations are necessarily write operations, so
    reset the default before beginning Alembic's transaction and fail with a
    direct diagnostic if the server is a genuine read replica.
    """
    if connection.dialect.name != "postgresql":
        return

    connection.exec_driver_sql("SET default_transaction_read_only = off")
    connection.commit()
    transaction_read_only = connection.exec_driver_sql(
        "SHOW transaction_read_only"
    ).scalar_one()
    connection.rollback()
    if transaction_read_only != "off":
        raise RuntimeError(
            "Alembic requires a writable PostgreSQL primary; "
            "transaction_read_only is still enabled"
        )
