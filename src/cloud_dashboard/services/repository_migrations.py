"""IGNIS Experiment Repository Migration Engine (Phase G4).

Manages SQLite schema version tracking using PRAGMA user_version and applies DDL migrations sequentially.
"""

import sqlite3
import logging

logger = logging.getLogger("repository_migrations")


class RepositoryMigrations:
    """Manages database schema creation and sequential version migrations for metadata.db."""

    CURRENT_VERSION = 1

    @classmethod
    def get_user_version(cls, conn: sqlite3.Connection) -> int:
        """Fetch current PRAGMA user_version from SQLite database."""
        cursor = conn.cursor()
        cursor.execute("PRAGMA user_version;")
        row = cursor.fetchone()
        return row[0] if row else 0

    @classmethod
    def set_user_version(cls, conn: sqlite3.Connection, version: int) -> None:
        """Set PRAGMA user_version in SQLite database."""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA user_version = {int(version)};")

    def migrate(self, db_path: str) -> None:
        """Connect to metadata.db, check PRAGMA user_version, and apply required migrations."""
        conn = sqlite3.connect(db_path)
        try:
            current = self.get_user_version(conn)
            logger.info(f"Checking metadata.db schema version: current={current}, target={self.CURRENT_VERSION}")

            if current < 1:
                self._migrate_v0_to_v1(conn)
                current = 1

            # Future schema migrations (v1 -> v2, etc.) can be chained here seamlessly

            logger.info(f"metadata.db schema migration complete. Active schema version: {current}")
        finally:
            conn.close()

    def _migrate_v0_to_v1(self, conn: sqlite3.Connection) -> None:
        """Initial DDL schema creation for Version 1."""
        logger.info("Executing DDL migration v0 -> v1...")
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id           TEXT PRIMARY KEY,
                directory               TEXT NOT NULL,
                timestamp               TEXT NOT NULL,
                archived_at             TEXT NOT NULL,
                seed                    INTEGER,
                git_commit              TEXT,
                trial_count             INTEGER,
                overall_verdict         TEXT NOT NULL,
                execution_duration_sec  REAL,
                platform_os             TEXT,
                platform_python         TEXT,
                platform_docker         TEXT,
                hostname                TEXT,
                regression_rules_hash   TEXT,
                manifest_sha256         TEXT NOT NULL,
                archive_schema_version  TEXT NOT NULL DEFAULT '1.0'
            );

            CREATE TABLE IF NOT EXISTS experiment_scenarios (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id           TEXT NOT NULL REFERENCES experiments(experiment_id) ON DELETE CASCADE,
                scenario_id             TEXT NOT NULL,
                verdict                 TEXT NOT NULL,
                duration_sec            REAL,
                trial_count             INTEGER,
                latency_mean            REAL,
                latency_ci_low          REAL,
                latency_ci_high         REAL
            );

            CREATE INDEX IF NOT EXISTS idx_exp_timestamp ON experiments(timestamp);
            CREATE INDEX IF NOT EXISTS idx_exp_verdict ON experiments(overall_verdict);
            CREATE INDEX IF NOT EXISTS idx_exp_commit ON experiments(git_commit);
            CREATE INDEX IF NOT EXISTS idx_scenario_exp ON experiment_scenarios(experiment_id);
            CREATE INDEX IF NOT EXISTS idx_scenario_verdict ON experiment_scenarios(verdict);
        """)

        self.set_user_version(conn, 1)
        conn.commit()
        logger.info("DDL migration v0 -> v1 successfully applied.")
