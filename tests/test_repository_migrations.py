"""Unit tests for RepositoryMigrations engine (Phase G4)."""

import os
import sqlite3
import tempfile
import pytest

from src.cloud_dashboard.services.repository_migrations import RepositoryMigrations


def test_repository_migrations_user_version():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_metadata.db")
        migrations = RepositoryMigrations()

        # Initially non-existent file, migrate creates schema v1
        migrations.migrate(db_path)
        assert os.path.exists(db_path)

        conn = sqlite3.connect(db_path)
        try:
            ver = migrations.get_user_version(conn)
            assert ver == 1

            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cursor.fetchall()]
            assert "experiments" in tables
            assert "experiment_scenarios" in tables

            cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
            indexes = [r[0] for r in cursor.fetchall()]
            assert "idx_exp_timestamp" in indexes
            assert "idx_exp_verdict" in indexes
            assert "idx_exp_commit" in indexes
        finally:
            conn.close()


def test_repository_migrations_idempotency():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_metadata.db")
        migrations = RepositoryMigrations()

        # First run
        migrations.migrate(db_path)
        # Second run should be safe and maintain v1
        migrations.migrate(db_path)

        conn = sqlite3.connect(db_path)
        try:
            assert migrations.get_user_version(conn) == 1
        finally:
            conn.close()
