# Example pipeline templates

Copy any `.json` file here into LDW via **Okapi panel → Pipelines → Import**, or place under `data/pipeline_templates/` for user templates.

Builtin templates ship in `config/pipeline_templates/`. These copies are for sharing with teammates or importing on a fresh install.

## Import steps

1. Open LDW → **Okapi** tab → **Pipelines**
2. Click **Import JSON** and select a template file
3. User templates appear with source `user` and can be exported or deleted from the UI

## Files

| File | Purpose |
|------|---------|
| `docx_xliff_roundtrip.json` | DOCX → XLIFF extract |
| `docx_okapi_roundtrip.json` | DOCX → XLIFF → merge back to DOCX |
| `docx_localize_basic.json` | Hermes Rung 2 default (extract; extend with TM/MT steps) |
| `format_conversion_xliff.json` | Generic format → XLIFF |
| `excel_to_tmx_qa.json` | Excel QA pipeline |
| `tmx_cleanup_optimization.json` | TMX cleanup |
