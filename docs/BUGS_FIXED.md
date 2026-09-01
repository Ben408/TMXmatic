# BUGS_FIXED.md — Language Data Workbench (TMXmatic)

| Date | Area | Fix |
|---|---|---|
| 2026-08-31 | `app.py` | **`get_application_path` was undefined** in `/api/check-feature` and `/api/install-feature` — now imported from `ldw_core.paths`. |
| 2026-08-31 | Core API | Added **`GET /health`**, **`GET /api/modules`**, and **local job API v1**. |
| 2026-08-31 | Okapi Phase 2 | Completed full integration — removed premature 2.1/2.2 deferrals; GHA + Longhorn + Python pipeline steps + builder UI now in core. |
| 2026-09-01 | Okapi UI build | Fixed missing parens in `okapi-panel.tsx` `while (Date.now() …)` — blocked Next.js production build on launch. |
| 2026-09-01 | XLIFF TMX leverage | Rewrote `xliff_operations.py` for XLIFF 1.2/2.0 + dynamic langs; UI calls `/api/xliff_tmx_leverage` with workspace TMX auto-pick. |
| 2026-09-01 | Docker tikal image | Replaced placeholder `okapiframework/okapi:latest` with `docker/okapi-tikal/Dockerfile` (Temurin 17 + okapi-apps 1.48.0); health check runs `tikal -info`. |
| 2026-09-01 | Tikal CLI | Okapi 1.48 uses `-od` output directory (not `-o`); runners normalize `*.docx.xlf` to registry artifact names. GHA workflow updated to match. |
| 2026-09-01 | Okapi XHTML extract | Intacct help XHTML fails with default `okf_html-wellFormed` (skeleton NPE + truncated XLF). Docker/local tikal now pass `-fc okf_html` for `.html`/`.htm`/`.xhtml`. |
| 2026-09-01 | Okapi extract targets | All tikal extract paths (`convert`, `qa`, `terms`) now pass `-nocopy` so XLIFF targets stay empty instead of copying source (required for TMX leverage). Filter `@param` overrides are not supported by tikal 1.48 CLI. |
| 2026-09-01 | Okapi cache | Reject corrupt/truncated XLIFF in `DockerTikalRunner` and `OkapiExecutor` cache — prevents bad cache hits after tikal exit 1. |
| 2026-09-01 | TMX leverage | Treat XLIFF targets that still copy source as untranslated; optional `target_lang` on `/api/xliff_tmx_leverage`. Phrase help TM e2e: 47/162 segments leveraged (fr-FR). |
| 2026-09-01 | GHA pilot | Private fork inbox 404 on raw URL — workflow downloads via Contents API + `github.token`; preserve input filename for tikal. |
| 2026-09-01 | GHA merge | Merge leg needs companion DOCX — `options_json.companion_url` in workflow; `okapi_smoke.py --roundtrip`. |
| 2026-09-01 | Okapi lang pair | Convert/merge without `-sl`/`-tl` — `tikal_options.py` defaults `en-us`/`fr-fr`; workflow passes lang flags. |
| 2026-09-01 | Lang retag | Standalone `scripts/lang_retag.py` — XLIFF file-level attrs only; TMX header + positional `tuv` find/replace (no regex in `seg`/`prop`). |

---

## Known issues (not fixed in Phase 1)

- Module Flask blueprints are **not** auto-registered — discovery via `modules.json` only.
- Okapi leverage match rate depends on Okapi segmentation vs Phrase TM source strings (markup/whitespace); expect partial coverage on help XHTML.
