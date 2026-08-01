# Phase G4 — Experiment Repository: Completion Walkthrough

Phase G4 equips IGNIS with a persistent, searchable experiment repository backed by a normalized SQLite index (`experiment_repository/metadata.db`) with built-in schema migration support and an interactive Repository Browser UI (`http://localhost:9000/repository`).

---

## Accomplished Features & Technical Architecture

1. **`RepositoryMigrations` Engine (`src/cloud_dashboard/services/repository_migrations.py`)**:
   - Manages SQLite schema versions using `PRAGMA user_version`.
   - Executes version 1 DDL DDL migrations creating `experiments` and `experiment_scenarios` tables with indexed columns (`idx_exp_timestamp`, `idx_exp_verdict`, `idx_exp_commit`, `idx_scenario_exp`, `idx_scenario_verdict`).

2. **`RepositoryManager` Sole Writer Service (`src/cloud_dashboard/services/repository_manager.py`)**:
   - Acts as the **sole writer** for `experiment_repository/`.
   - Implements **Atomic Staging Archival**: copies outputs into `.tmp_{exp_id}` staging directory before performing an atomic folder rename to `experiment_repository/YYYY-MM-DD_HH-MM-SS_{exp_id}/`.
   - Computes `manifest_sha256` SHA-256 integrity hash for `experiment_manifest.json`.
   - Executes SQLite explicit `BEGIN TRANSACTION` / `COMMIT` / `ROLLBACK` blocks for relational metadata insertion.
   - Enforces immutability policy (archived folders are never modified or overwritten).

3. **Read-Only REST API Endpoints (`src/cloud_dashboard/routes/repository.py`)**:
   - `GET /api/v1/repository`: Strictly read-only query endpoint supporting filtering (`verdict`, `scenario`, `commit`, `from_date`, `to_date`), sorting (`timestamp`, `duration`, `verdict`, `trials`), and pagination.
   - `GET /api/v1/repository/{experiment_id}`: Detail endpoint returning full experiment metadata, scenario breakdown, file manifest, and report links.
   - `GET /api/v1/repository/{experiment_id}/report.html`: Serves archived interactive HTML report.

4. **Repository Browser UI (`src/cloud_dashboard/templates/repository.html`)**:
   - Timeline browser displaying archived runs sorted Newest First by default.
   - Interactive search & filter toolbar for verdict, scenario, commit hash, and sort criteria.
   - Expandable experiment cards showing scenario metrics table, `manifest_sha256` hash, archive schema version (`1.0`), and direct links to view HTML reports.
   - Updated navigation sidebar (`navbar.html`) highlighting active **Repository** tab.

5. **Automatic ProcessManager Integration (`process_manager.py`)**:
   - Subprocess completion or failure automatically triggers `RepositoryManager().archive_experiment()` upon state transition to `COMPLETED` or `FAILED`.

---

## Test Results Summary

11 out of 11 tests passed in 1.69s:

```powershell
python -m pytest tests/test_repository_migrations.py tests/test_repository_manager.py tests/test_repository_api.py tests/test_repository_ui.py -v
```

```
======================== 11 passed in 1.69s ========================
```

- **`test_repository_migrations.py`**: Passed (2/2)
- **`test_repository_manager.py`**: Passed (3/3)
- **`test_repository_api.py`**: Passed (4/4)
- **`test_repository_ui.py`**: Passed (2/2)
