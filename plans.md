# Eden Framework: ORM & Testing Stability Plan

This plan details the steps to resolve ORM failures and stabilize the testing infrastructure for the Eden Framework, specifically addressing Windows-specific file locking issues and fragile session/join logic.

## Feature Layers

### Layer 1: Testing Infrastructure (Stability)
- [x] **Standardize Database Fixtures**: Ensure `conftest.py` uses in-memory or unique temp SQLite files for audit tests to avoid Windows `PermissionError`. (Implemented in `eden/testing.py` using in-memory SQLite by default).
- [x] **Pool Connection Cleanup**: Verify `Database.disconnect()` properly closes all SQLAlchemy engine connections. (Implemented using `yield` and `finally` block in `test_app` fixture).
- [x] **Reliable Metadata Registration**: Ensure all models are imported before `metadata.create_all` is called in test setups. (Proactively importing core models in `test_app`).
- **Status**: [COMPLETED]

### Layer 2: ORM Session Management
- [x] **Strict Session Resolution**: Modify `QuerySet._provide_session` in `eden/db/query.py` to properly handle context sessions. (Added `is_active` check and better resolution order).
- [x] **Session Error Clarity**: Raise `SessionResolutionError` (or similar descriptive error) when a query is executed without an active session context. (Added `SessionResolutionError` to `eden/db/session.py`).
- [x] **Transaction Guarding**: Ensure queries within a transaction block *must* use the transactional session. (Implemented via `is_active` validation and improved `_provide_session`).
- **Status**: [COMPLETED]

### Layer 3: Relationship & Join Logic
- [x] **Deep Path Inference**: Enhance `find_relationship_path` in `eden/db/lookups.py` to correctly bridge deep paths (e.g., `GrandParent -> Parent -> Child`). (Implemented using robust BFS with `max_depth=5`).
- [x] **Involvement Detection**: Improve `extract_involved_models` to accurately identify all models required for a complex query filter. (Added support for `AliasedClass`, `Column`, and direct `InstrumentedAttribute`).
- [x] **Auto-Join Verification**: Validate that inferred joins produce correct SQLAlchemy `join()` clauses. (Verified via `tests/test_orm_enhanced.py`).
- **Status**: [COMPLETED]

---

## Integration Validation
- [x] Trace data flow through all three layers.
- [x] Run full test suite on Windows environment.
- [x] Verify documentation matches the updated session/join behavior.


For postgres testing use:
* Username: postgres
* Password: 0123456789
* Database: eden_tests
* Host: localhost
* Port: 5432