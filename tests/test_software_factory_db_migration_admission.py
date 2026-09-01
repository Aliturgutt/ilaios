"""SF-20 migration admission path-selection tests."""

from services.software_factory_db_migration_admission import is_real_migration_path


def test_real_migration_paths_are_selected() -> None:
    assert is_real_migration_path("db/migrations/0001_init.py") is True
    assert is_real_migration_path("alembic/versions/0002_expand.py") is True
    assert is_real_migration_path("schema/0003_backfill.sql") is True
    assert is_real_migration_path("services/control_plane/migrations.py") is True


def test_sf20_implementation_and_tests_are_not_scan_subjects() -> None:
    assert (
        is_real_migration_path("services/software_factory_db_migration_safety.py")
        is False
    )
    assert (
        is_real_migration_path("tests/test_software_factory_db_migration_safety.py")
        is False
    )
    assert is_real_migration_path("docs/governance/SF20_DB_MIGRATION_SAFETY.md") is False
