# BUGS_FIXED.md — Language Data Workbench (TMXmatic)

| Date | Area | Fix |
|---|---|---|
| 2026-08-31 | `app.py` | **`get_application_path` was undefined** in `/api/check-feature` and `/api/install-feature` — now imported from `ldw_core.paths`. |
| 2026-08-31 | Core API | Added **`GET /health`**, **`GET /api/modules`**, and **local job API v1**. |
| 2026-08-31 | Okapi Phase 2 | Completed full integration — removed premature 2.1/2.2 deferrals; GHA + Longhorn + Python pipeline steps + builder UI now in core. |
| 2026-08-31 | Okapi runners | Fixed circular import between `runners.py` and `github_runner.py` via lazy imports in `build_runner()`. |

---

## Known issues (not fixed in Phase 1)

- Okapi integration remains **hosted workspace client only** (`integration_apis.py`); Docker tikal runner not yet implemented.
- Module Flask blueprints are **not** auto-registered — discovery via `modules.json` only.
