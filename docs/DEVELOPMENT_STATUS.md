# DEVELOPMENT_STATUS.md — Language Data Workbench (TMXmatic)

| Field | Value |
|---|---|
| **Last updated** | 2026-08-31 |
| **Current phase** | **Phase 1 — LDW core prerequisites** (in progress) |
| **Repo** | [Ben408/TMXmatic](https://github.com/Ben408/TMXmatic) (public OSS) |
| **Local path** | `F:\Language Data Workbench` |
| **Planning (private)** | [Ben408/LDW-Planning](https://github.com/Ben408/LDW-Planning) |

---

## Phase 1 deliverables (ldw-core-prerequisites)

| # | Item | Status |
|---|---|---|
| 1 | `modules.json` schema + example | ✅ `modules.json.example`, `docs/MODULE_INSTALL.md` |
| 2 | `install.bat` contract documented | ✅ `docs/MODULE_INSTALL.md` |
| 3 | Local job API v1 | ✅ `POST/GET /api/jobs`, artifacts, cancel |
| 4 | Pipeline step registry (core catalog) | ✅ `ldw_core/pipeline_registry.py`, `GET /api/pipeline-steps` |
| 5 | `GET /api/modules` | ✅ |
| 6 | `GET /health` | ✅ |
| 7 | Okapi runner abstraction | ⏳ Phase 2+ |

---

## Implemented (Phase 1)

- **`ldw_core/`** package: module registry, job manager, API blueprint
- **Flask routes** registered from `app.py` (no Hermes dependency)
- **Unit + HTTP tests** under `tests/` (`pytest`)
- **Core version** `1.3.0` in `ldw_core/version.py`

---

## Next (Phase 2+)

- Okapi Docker tikal runner + DOCX round-trip
- Module blueprint auto-registration from `manifest.json`
- Wire `ldw-llm-quality` via `install.bat`
- Hermes Slack document-translate job glue (polls local job API)

---

## Verification

```powershell
cd "F:\Language Data Workbench"
.\.venv\Scripts\python.exe -m pip install -r other\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q
```

With LDW running: `curl http://127.0.0.1:5000/health`

---

## Related repos

| Repo | Role |
|---|---|
| LDW-Planning | Architecture + backlog (private) |
| ldw-llm-quality | XLIFF QA module (private WIP) |
| ldw-multi-agent | TM/style module (private WIP) |
| ldw-okapi-workflows | User GHA Okapi template (private WIP) |
| Hermes-Local | Slack orchestration (calls LDW HTTP only) |
