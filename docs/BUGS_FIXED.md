# BUGS_FIXED.md — Language Data Workbench (TMXmatic)

| Date | Area | Fix |
|---|---|---|
| 2026-08-31 | `app.py` | **`get_application_path` was undefined** in `/api/check-feature` and `/api/install-feature` — now imported from `ldw_core.paths`. |
| 2026-08-31 | Core API | Added **`GET /health`**, **`GET /api/modules`**, and **local job API v1**. |
| 2026-08-31 | Okapi Phase 2 | Completed full integration — removed premature 2.1/2.2 deferrals; GHA + Longhorn + Python pipeline steps + builder UI now in core. |
| 2026-09-01 | Okapi UI build | Fixed missing parens in `okapi-panel.tsx` `while (Date.now() …)` — blocked Next.js production build on launch. |
| 2026-09-01 | Workspace upload | Drop zone only allowed TMX/Excel/XLIFF — `.docx` and other Okapi formats were silently rejected; extended `WORKSPACE_UPLOAD_EXTENSIONS` to match `okapi_operations.yml`. |
| 2026-09-01 | Docker tikal image | Replaced placeholder `okapiframework/okapi:latest` with `docker/okapi-tikal/Dockerfile` (Temurin 17 + okapi-apps 1.48.0); health check runs `tikal -info`. |
| 2026-09-01 | Tikal CLI | Okapi 1.48 uses `-od` output directory (not `-o`); runners normalize `*.docx.xlf` to registry artifact names. GHA workflow updated to match. |

---

## Known issues (not fixed in Phase 1)

- Okapi integration remains **hosted workspace client only** (`integration_apis.py`); Docker tikal runner not yet implemented.
- Module Flask blueprints are **not** auto-registered — discovery via `modules.json` only.
