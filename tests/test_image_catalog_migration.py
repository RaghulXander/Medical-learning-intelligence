import importlib
from unittest.mock import patch

import pytest


migration = importlib.import_module(
    "migrations.versions.20260903_0007_image_evidence_catalog"
)


class CatalogInspector:
    def __init__(self, *, tables=None, remove_column=None):
        self.tables = tables or set(migration.TABLE_NULLABILITY)
        self.remove_column = remove_column

    def get_table_names(self):
        return list(self.tables)

    def get_columns(self, table_name):
        return [
            {"name": name, "nullable": nullable}
            for name, nullable in migration.TABLE_NULLABILITY[table_name].items()
            if (table_name, name) != self.remove_column
        ]

    def get_pk_constraint(self, table_name):
        return {"constrained_columns": ["id"]}

    def get_foreign_keys(self, table_name):
        return [
            {"constrained_columns": [column], "referred_table": target}
            for column, target in migration.REQUIRED_FOREIGN_KEYS[table_name]
        ]

    def get_indexes(self, table_name):
        return [
            {"column_names": list(columns), "unique": unique, "name": name}
            for columns, unique, name in migration.REQUIRED_INDEXES[table_name]
        ]

    def get_unique_constraints(self, table_name):
        return []


def test_upgrade_adopts_complete_compatible_preexisting_catalog():
    inspector = CatalogInspector()
    with (
        patch.object(migration.op, "get_bind", return_value=object()),
        patch.object(migration.sa, "inspect", return_value=inspector),
        patch.object(migration.op, "create_table") as create_table,
        patch.object(migration.op, "create_index") as create_index,
    ):
        migration.upgrade()

    create_table.assert_not_called()
    create_index.assert_not_called()


def test_upgrade_rejects_partial_preexisting_catalog():
    inspector = CatalogInspector(tables={"image_assets"})
    with (
        patch.object(migration.op, "get_bind", return_value=object()),
        patch.object(migration.sa, "inspect", return_value=inspector),
        pytest.raises(RuntimeError, match="partial image catalog"),
    ):
        migration.upgrade()


def test_upgrade_rejects_incompatible_preexisting_catalog():
    inspector = CatalogInspector(remove_column=("image_assets", "rights_status"))
    with (
        patch.object(migration.op, "get_bind", return_value=object()),
        patch.object(migration.sa, "inspect", return_value=inspector),
        pytest.raises(RuntimeError, match="missing columns: rights_status"),
    ):
        migration.upgrade()
