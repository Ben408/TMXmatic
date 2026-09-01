# DEVELOPMENT_STATUS.md — Language Data Workbench (TMXmatic)

| Field | Value |
|---|---|
| **Last updated** | 2026-08-31 |
| **Current phase** | **Phase 2 — Okapi integration** (in progress) |
| **Repo** | [Ben408/TMXmatic](https://github.com/Ben408/TMXmatic) (public OSS) |
| **Local path** | `F:\Language Data Workbench` |
| **Planning (private)** | [Ben408/LDW-Planning](https://github.com/Ben408/LDW-Planning) |

---

## Phase 1 — complete ✅

| # | Item | Status |
|---|---|---|
| 1 | `modules.json` schema + example | ✅ |
| 2 | `install.bat` contract documented | ✅ |
| 3 | Local job API v1 | ✅ |
| 4 | Pipeline step registry (core catalog) | ✅ |
| 5 | `GET /api/modules` | ✅ |
| 6 | `GET /health` | ✅ |

---

## Phase 2 — Okapi (started 2026-08-31)

Spec: `LDW-Planning/backlog/OKAPI_INTEGRATION_PLAN_rev.md`

| # | Item | Status |
|---|---|---|
| 1 | Operation registry (`config/okapi_operations.yml`) | ✅ |
| 2 | Runner abstraction (Docker, local tikal, GHA/Longhorn stubs, hosted) | ✅ |
| 3 | Okapi job types (`okapi-operation`, `pipeline`) | ✅ |
| 4 | API: submit-upload, submit-url, status, results, backends | ✅ |
| 5 | Hybrid pipeline manager + DOCX→XLIFF template | ✅ |
| 6 | GUI: `OkapiPanel` + Settings backend selector | ✅ |
| 7 | Idempotent artifact cache (`data/okapi_cache/`) | ✅ |
| 8 | GitHub Actions runner (user fork) | ⏳ stub |
| 9 | Longhorn pipeline API | ⏳ stub |
| 10 | Full Python+Okapi mixed pipeline steps | ⏳ Phase 2.1 |
| 11 | Pipeline Builder wizard UI | ⏳ Phase 2.2 |

---

## API summary (Phase 1 + 2)

| Endpoint | Purpose |
|---|---|
| `GET /health` | Wake probe |
| `GET /api/modules` | Installed modules |
| `POST /api/jobs` | Generic local jobs |
| `GET /api/okapi/operations` | Registry-driven Okapi ops |
| `GET /api/okapi/backends/status` | Docker/GHA/Longhorn/hosted probes |
| `POST /api/okapi/submit-upload` | Multipart → Okapi job |
| `POST /api/okapi/submit-url` | URL download → Okapi job |
| `GET /api/pipeline-templates` | Predefined pipelines |
| `POST /api/pipelines/execute` | Run hybrid pipeline job |

---

## Verification

```powershell
cd "F:\Language Data Workbench"
.\.venv\Scripts\python.exe -m pip install -r other\requirements.txt -r other\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q
# 27 passed
```

Docker pilot: enable Okapi in Settings → backend **docker** → pull/use `okapiframework/okapi:latest`.

---

## Next

- Wire `ldw-okapi-workflows` GHA fork (presigned URL flow per spec)
- Python step handlers in hybrid pipeline (merge TM, leverage XLIFF)
- Hermes document-translate glue (poll job API)
