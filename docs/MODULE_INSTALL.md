# Module install contract (LDW core Phase 1)

**Applies to:** [Ben408/TMXmatic](https://github.com/Ben408/TMXmatic)  
**Planning spec:** `F:/LDW-Planning/architecture/module-system.md`

Modules are **not** installed via pip. Each module ships an **`install.bat`** that copies files into the LDW tree and registers in **`modules.json`**.

---

## Layout after install

```text
%LDW_HOME%/
  modules.json              ← core-owned registry (see modules.json.example)
  modules/
    <module_id>/
      manifest.json         ← routes, ui_panels, pipeline_steps, health_check
      install.bat           ← idempotent installer (module repo root)
      ... module code ...
  .venv/                    ← shared Python environment (pip install -r requirements.txt)
```

---

## `install.bat` steps (contract)

1. **Resolve `LDW_HOME`** — default `%CD%` parent or env `LDW_HOME` (e.g. `F:\Language Data Workbench`).
2. **Verify LDW core** — `GET http://127.0.0.1:5000/health` returns `status: ok` (optional but recommended).
3. **Copy files** → `%LDW_HOME%\modules\<module_id>\`
4. **`pip install -r requirements.txt`** into `%LDW_HOME%\.venv` (GPU extras via `requirements-gpu.txt` when present).
5. **Register module** in `%LDW_HOME%\modules.json` (merge by `id`, do not wipe other modules).
6. **Optional:** register UI panels / pipeline steps declared in `manifest.json`.

Uninstall (future): remove registry row; do **not** delete core LDW files.

---

## `modules.json` schema v1

| Field | Required | Description |
|---|---|---|
| `schema_version` | yes | Always `1` for local v1 |
| `modules[]` | yes | Installed module rows |
| `modules[].id` | yes | Stable id (e.g. `ldw-llm-quality`) |
| `modules[].version` | yes | Module semver |
| `modules[].ldw_min` | yes | Minimum compatible LDW core version |
| `modules[].ldw_max` | no | Maximum compatible LDW core (inclusive) |
| `modules[].gpu_required` | no | Default `false` |
| `modules[].installed_at` | no | ISO-8601 UTC timestamp |
| `modules[].manifest_path` | yes | Relative path under `LDW_HOME` |

Core exposes **`GET /api/modules`** with a `compatible` flag per row (semver check against running core).

---

## Per-module `manifest.json` (module-owned)

Expected keys (module-specific):

- `routes` — Flask blueprint registration hooks
- `ui_panels` — New_UI component ids
- `pipeline_steps` — job step types (e.g. `translate-xliff-qa`)
- `health_check` — optional path under `/api/modules/<id>/health`

Module registration into Flask is **Phase 2+**; Phase 1 only reads `modules.json` for discovery.

---

## API discovery (Hermes / Slack)

| Endpoint | Purpose |
|---|---|
| `GET /health` | Wake probe |
| `GET /api/modules` | Installed capabilities + compatibility |
| `POST /api/jobs` | Start local background job |
| `GET /api/jobs/{id}` | Poll status |
| `GET /api/jobs/{id}/artifacts/{name}` | Download output |
| `POST /api/jobs/{id}/cancel` | Cancel in-flight job |

SaaS breaking changes tracked in `F:/LDW-Planning/saas-migration/breaking-change-registry.md` (ID **S001** job poll → webhooks).
