# DEVELOPMENT_STATUS.md — Language Data Workbench (TMXmatic)

| Field | Value |
|---|---|
| **Last updated** | 2026-08-31 |
| **Current phase** | **Phase 2 — Okapi integration** ✅ core complete |
| **Repo** | [Ben408/TMXmatic](https://github.com/Ben408/TMXmatic) |
| **Local path** | `F:\Language Data Workbench` |

---

## Phase 2 — Okapi (complete)

Full Okapi surfaces per `LDW-Planning/backlog/OKAPI_INTEGRATION_PLAN_rev.md`:

| Capability | Status |
|---|---|
| Canonical operation registry (`config/okapi_operations.yml`) | ✅ |
| Backends: Docker tikal, local tikal, GitHub Actions, Longhorn, hosted workspace | ✅ |
| Job API: `okapi-operation`, `pipeline` | ✅ |
| `submit-upload` / `submit-url` / `status` / `results` | ✅ |
| Hybrid Python + Okapi pipelines | ✅ |
| Pipeline templates (builtin + user save) | ✅ |
| Discovery: `/api/okapi/auto-discover`, github/external ops | ✅ |
| `POST /api/execute-pipeline` | ✅ |
| GUI: Okapi ops + pipelines + **pipeline builder** tabs | ✅ |
| Settings: all backend credentials | ✅ |
| GHA workflow: `.github/workflows/okapi-ops.yml` | ✅ |
| Idempotent artifact cache | ✅ |

---

## Verification

```powershell
cd "F:\Language Data Workbench"
.\.venv\Scripts\python.exe -m pytest tests -q
# 34 passed
```

### Backend setup

| Backend | Settings |
|---|---|
| **docker** (default) | Docker running + `docker_image` |
| **local_tikal** | `tikal_path` to tikal.bat/sh |
| **github** | `github_token`, `github_repo` (fork of [ldw-okapi-workflows](https://github.com/Ben408/ldw-okapi-workflows)) |
| **longhorn** | `longhorn_url` to external Okapi API |
| **hosted** | Existing workspace API key/url/id |

---

## Next (Phase 3+)

- `ldw-llm-quality` module install + XLIFF QA pipeline steps
- Hermes Slack document-translate job glue
- Okapi DOCX round-trip pilot on production Docker host
