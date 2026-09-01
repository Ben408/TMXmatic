# BUGS_FIXED.md — Language Data Workbench (TMXmatic)

| Date | Area | Fix |
|---|---|---|
| 2026-08-31 | `app.py` | **`get_application_path` was undefined** in `/api/check-feature` and `/api/install-feature` — now imported from `ldw_core.paths`. |
| 2026-08-31 | Core API | Added **`GET /health`**, **`GET /api/modules`**, and **local job API v1**. |
| 2026-08-31 | Okapi Phase 2 | **`HostedWorkspaceRunner`** health probe no longer fails entire `/api/okapi/backends/status` when optional deps misconfigured — per-backend try/except. |
| 2026-08-31 | Okapi Phase 2 | Fixed **`ALL_BACKENDS` NameError** in `resolve_active_backend()`. |

---

## Known issues (not fixed in Phase 1)

- Okapi integration remains **hosted workspace client only** (`integration_apis.py`); Docker tikal runner not yet implemented.
- Module Flask blueprints are **not** auto-registered — discovery via `modules.json` only.
