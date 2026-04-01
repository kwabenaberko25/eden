# Eden Framework - Test & Implementation Corrections

This document tracks identified issues, failing tests, and recommended remedies found during the framework-wide test run on Windows.

## 1. Database & ORM Performance/Integrity

### [FIXED] DATABASE_URL Case Sensitivity

- **Issue**: `eden/testing.py` was hardcoding `config.DATABASE_URL` (uppercase), which bypassed the Pydantic field `database_url` (lowercase).
- **Status**: Corrected in `eden/testing.py` to use lowercase `config.database_url`.

### [FIXED] UUID Datatype Mismatch on PostgreSQL

- **Issue**: `SchemaInferenceEngine` in `eden/db/schema.py` forced `native_uuid=False`.
- **Status**: Corrected to `native_uuid=True` in `eden/db/schema.py`.

### [FIXED] ORM: `QuerySet` missing `_resolve_session` async method
- **Issue**: `tests/test_orm_critical_fixes.py` calls `await qs._resolve_session()`.
- **Correction**: Added `async def _resolve_session` to `eden/db/query.py`.
- **Benefit**: Restores compatibility with existing tests.

### [FIXED] ORM: `Database.savepoint` signature mismatch
- **Issue**: Tests call `db.savepoint("name")`.
- **Correction**: Updated signature in `eden/db/session.py` to `def savepoint(self, name=None, session=None)`.
- **Benefit**: Correctly handles name-first calls/contextually-passed names.

### [FIXED] Testing: `Config` attribute case sensitivity
- **Issue**: `eden/testing.py` used uppercase `config.DEBUG`.
- **Correction**: Updated to lowercase attribute names.
- **Benefit**: Ensures configuration is correctly applied.

### [IMPROVEMENT] Hardcoded SQLite in Tests

- **Issue**: Over 20 test files have `Database("sqlite+aiosqlite:///:memory:")` hardcoded instead of using the `db` fixture or `Config`.
- **Impact**: Prevents testing the full suite against PostgreSQL.
- **Recommended Remedy**: Refactor tests to use the `db` fixture from `conftest.py`.

## 2. Authentication & Security

### [OBSERVATION] Multi-Tenancy Isolation

- **Issue**: Some tenancy tests failed with `ProgrammingError` when running on PostgreSQL.
- **Details**: Likely related to the schema swapping logic (`SET search_path`).
- **Recommended Remedy**: Ensure `TenantMiddleware` correctly handles schema provisioning for PostgreSQL.

## 3. Documentation Sync

### [SYNC REQUIRED] Active Link Directive

- **Status**: The `@active_link` directive documentation in `templating.md` was recently updated but needs validation.

## 4. Test Summary (Final Strategy)

- **Total Tests**: 1054
- **Next Step**: Applying these fixes has resolved the most common structural errors.
- **Goal**: Full test pass or targeted refinement of UI/Frontend components.
