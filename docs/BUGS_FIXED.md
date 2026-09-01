# BUGS_FIXED.md — Language Data Workbench (TMXmatic)

| Date | Area | Fix |
|---|---|---|
| 2026-08-31 | `app.py` | **`get_application_path` was undefined** in `/api/check-feature` and `/api/install-feature` — now imported from `ldw_core.paths` (shared with launcher). |
| 2026-08-31 | Core API | Added **`GET /health`**, **`GET /api/modules`**, and **local job API v1** so Hermes can wake/probe LDW without importing Hermes into core. |

---

## Known issues (not fixed in Phase 1)

- Okapi integration remains **hosted workspace client only** (`integration_apis.py`); Docker tikal runner not yet implemented.
- Module Flask blueprints are **not** auto-registered — discovery via `modules.json` only.
