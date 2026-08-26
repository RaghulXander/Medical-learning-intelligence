# Database migrations

Alembic is the production schema authority beginning with Milestone 10.

```bash
alembic current
alembic upgrade head
alembic history
```

The baseline revision is intentionally idempotent: it creates the current SQLAlchemy schema on a fresh database and leaves existing tables intact. Before applying it to an existing environment, take a backup and verify that the database was initialized by the current application version.

New model changes must include a reviewed Alembic revision. Do not add new runtime `ALTER TABLE` compatibility statements.
