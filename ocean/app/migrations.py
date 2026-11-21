# Copyright (c) 2024
#
# This file is part of OCEAN.
#
# OCEAN is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OCEAN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OCEAN.  If not, see <https://www.gnu.org/licenses/>.

"""Database migrations.

Schema changes are SQL files in `ocean/migrations/`, applied in filename order. Each applied file
is recorded in the `schema_migrations` table, so every file runs exactly once per database.
`migrate()` runs when the app starts (see `database_handler.init_db`).

The baseline schema is `db-init/create_database.sql`, which creates a new database (automatically
in docker, or by hand for a manual install). Migrations are only applied on top of it.

Writing a migration:
- Name the file `YYYY-MM-DD_short_description.sql` so files sort in the order they were written.
- Never edit a migration that has been merged; add a new one instead.
- Separate statements with `;` at the end of a line (no `;` inside strings or comments).
- MariaDB cannot roll back schema changes, so keep each file small and, where possible, make it
  safe to re-run (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, `DROP COLUMN IF EXISTS`).
- Altering system-versioned tables is allowed (`system_versioning_alter_history` is set to KEEP).
"""

# Standard library imports
import os

# Local application imports
from .logger import logger

MIGRATIONS_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrations")
LOCK_NAME = "ocean_migrations"
LOCK_TIMEOUT_SECONDS = 600


def split_statements(sql: str) -> list:
    """Split a SQL script into statements, dropping `--` comment lines."""
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    statements, current = [], []
    for line in lines:
        current.append(line)
        if line.rstrip().endswith(";"):
            statements.append("\n".join(current).strip().rstrip(";"))
            current = []
    if "".join(current).strip(): statements.append("\n".join(current).strip())
    return [s for s in statements if s]

def pending_migrations(applied: set) -> list:
    """The migration file names that have not been applied, in the order they should run."""
    files = sorted(f for f in os.listdir(MIGRATIONS_DIRECTORY) if f.endswith(".sql"))
    return [f for f in files if f not in applied]

def migrate(engine) -> list:
    """Apply all pending migrations to the database and return the names of those applied.
    Raises if a migration fails, leaving the migrations before it recorded as applied."""
    applied_now = []
    with engine.connect() as conn:
        # Only one process migrates at a time (e.g. several production workers starting together)
        if conn.exec_driver_sql(f"SELECT GET_LOCK('{LOCK_NAME}', {LOCK_TIMEOUT_SECONDS})").scalar() != 1:
            raise RuntimeError("Timed out waiting for another process to finish database migrations.")
        try:
            if not conn.exec_driver_sql("SHOW TABLES LIKE 'selection'").first():
                raise RuntimeError("The database has not been initialised. Create it with db-init/create_database.sql first.")
            conn.exec_driver_sql("""CREATE TABLE IF NOT EXISTS `schema_migrations` (
                `name` varchar(255) NOT NULL,
                `applied_datetime` timestamp NOT NULL DEFAULT current_timestamp(),
                PRIMARY KEY (`name`)
            ) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci""")
            conn.exec_driver_sql("SET @@session.system_versioning_alter_history = 1")
            applied = {row[0] for row in conn.exec_driver_sql("SELECT name FROM schema_migrations")}
            for name in pending_migrations(applied):
                logger.info(f"Applying database migration {name}")
                with open(os.path.join(MIGRATIONS_DIRECTORY, name)) as f:
                    for statement in split_statements(f.read()):
                        conn.exec_driver_sql(statement)
                conn.exec_driver_sql("INSERT INTO schema_migrations (name) VALUES (%s)", (name,))
                conn.commit()
                applied_now.append(name)
        finally:
            conn.exec_driver_sql(f"SELECT RELEASE_LOCK('{LOCK_NAME}')")
    return applied_now
