import os
import re
import uuid

import pytest
import sqlalchemy

from ..app import migrations

### Migration files ###

def test_migration_file_names():
    files = [f for f in os.listdir(migrations.MIGRATIONS_DIRECTORY) if f.endswith(".sql")]
    assert files, "No migrations found"
    for f in files:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_[a-z0-9_]+\.sql", f), f"Migration {f} should be named YYYY-MM-DD_description.sql"

def test_pending_migrations_are_sorted_and_skip_applied():
    files = sorted(f for f in os.listdir(migrations.MIGRATIONS_DIRECTORY) if f.endswith(".sql"))
    assert migrations.pending_migrations(set()) == files
    assert migrations.pending_migrations(set(files)) == []

def test_split_statements():
    sql = """-- a comment; with a semicolon
CREATE TABLE a (
  id int
);
/*!40101 SET NAMES utf8mb4 */;

INSERT INTO a VALUES (1)"""
    assert migrations.split_statements(sql) == [
        "CREATE TABLE a (\n  id int\n)",
        "/*!40101 SET NAMES utf8mb4 */",
        "INSERT INTO a VALUES (1)",
    ]


### Applying migrations to a real database ###
# Runs against the MariaDB server given by OCEAN_TEST_MARIADB_URL (by default the one used in CI).
# A temporary database is created from db-init/create_database.sql and dropped afterwards.

SERVER_URL = os.environ.get("OCEAN_TEST_MARIADB_URL", "mysql+mysqldb://root:test123@localhost:3306")

@pytest.fixture
def baseline_engine():
    try:
        server = sqlalchemy.create_engine(SERVER_URL)
        with server.connect(): pass
    except Exception as e:
        pytest.skip(f"No MariaDB server available at OCEAN_TEST_MARIADB_URL: {e}")
    name = f"ocean_migration_test_{uuid.uuid4().hex[:8]}"
    with server.connect() as conn:
        conn.exec_driver_sql(f"CREATE DATABASE `{name}`")
    engine = sqlalchemy.create_engine(f"{SERVER_URL}/{name}")
    try:
        with open("db-init/create_database.sql") as f, engine.connect() as conn:
            for statement in migrations.split_statements(f.read()):
                conn.exec_driver_sql(statement)
            conn.commit()
        yield engine
    finally:
        engine.dispose()
        with server.connect() as conn:
            conn.exec_driver_sql(f"DROP DATABASE `{name}`")
        server.dispose()

def test_migrate_applies_each_migration_once(baseline_engine):
    applied = migrations.migrate(baseline_engine)
    assert applied == migrations.pending_migrations(set())
    assert migrations.migrate(baseline_engine) == []  # nothing left to apply
    with baseline_engine.connect() as conn:
        recorded = {row[0] for row in conn.exec_driver_sql("SELECT name FROM schema_migrations")}
        tables = {row[0] for row in conn.exec_driver_sql("SHOW TABLES")}
        encounter_columns = {row[0] for row in conn.exec_driver_sql("SHOW COLUMNS FROM encounter")}
    assert recorded == set(applied)
    assert {"classifier", "selection_classification"} <= tables
    assert "classifier_id" in encounter_columns

def test_migrate_refuses_uninitialised_database(baseline_engine):
    with baseline_engine.connect() as conn:
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
        conn.exec_driver_sql("DROP TABLE selection")
    with pytest.raises(RuntimeError, match="not been initialised"):
        migrations.migrate(baseline_engine)
