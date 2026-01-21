# TMXmatic — TQE Module (Translation Quality Estimation)

This document describes the Translation Quality Estimation (TQE) module provided for TMXmatic. It explains architecture, configuration, CLI usage, integration points (TMX, TBX/CSV termbases, UQLM), COMET / COMET-QE integration, fuzzy TM matching, terminology enforcement policies (user-selectable), prompt injection into the LLM stage, calibration, testing, and how metadata is written back to XLIFF.

This README is written for developers integrating or testing the module in Ben408/TMXmatic.

Table of contents
- Overview
- High-level architecture
- Inputs and outputs
- Installation & models
- COMET / COMET-QE download helper
- CLI usage & flags
- Terminology integration & prompt injection
- Term enforcement policies (UI mapping)
- Fuzzy TM matching behavior
- Metric computation & aggregation logic
- Calibration (how-to)
- XLIFF metadata (props written)
- Integration with TMXmatic UI (mapping to flags)
- Testing (synthetic dataset)
- Performance & GPU tuning (RTX 12GB)
- Troubleshooting
- References & datasets
- Files included in this module

---

Overview
--------
This module evaluates candidate translations (from an LLM / NMT) and chooses the best candidate to store into an XLIFF TU. It computes per-candidate scores for:
- Accuracy (adequacy / faithfulness) — using COMET (ref-based) when a human reference exists, otherwise COMET-QE (no-ref) or BERTScore/SBERT fallback.
- Fluency — LM-based perplexity -> normalized score.
- Tone-of-Voice — sentence-embedding similarity to tone exemplars (SBERT).
- Term-match — checks for approved terminology usage from TBX/CSV termbase (exact/fuzzy/compound-aware).

The module incorporates UQLM (factuality/hallucination) outputs and applies penalties or hard decisions as configured.

It writes chosen translation and a structured set of metadata (tqe:* props) back into the XLIFF TU for auditing and downstream use.

High-level architecture
-----------------------
- Input: XLIFF file + candidates JSON (mapping tu_id or source -> list of candidate strings)
- Optional inputs:
  - TMX file (translation memory)
  - Termbases (CSV or TBX)
  - UQLM JSON (per-TU hallucination results)
  - Tone exemplars JSON (per-TU or default tone exemplar list)
  - Optional calibration JSON (to map raw model outputs to human scale)
- Models (optional, GPU-enabled):
  - COMET (reference-based) checkpoint
  - COMET-QE (no-ref) checkpoint
  - Causal LM for fluency (HF model)
  - SentenceTransformers (SBERT) for tone & similarity
  - BERTScore (fallback accuracy when ref present)
- Processing order for reference selection:
  1. Exact TMX match (highest priority)
  2. High fuzzy TMX match (Levenshtein-based; configurable threshold)
  3. Existing XLIFF target marked as human (if enabled or allowed)
  4. LLM candidates (fallback)
- Output: Updated XLIFF with chosen target and `prop-group` props containing per-metric and aggregate metadata.

Inputs and outputs
------------------
Inputs:
- --xliff <path> (required)
- --candidates <path> (required) — JSON mapping of TU id or source text -> [candidate strings]
- Optional:
  - --tmx <path>
  - --terms_csv <path>
  - --terms_tbx <path>
  - --uqlm <path> (UQLM JSON)
  - --tone_exemplars <path> (JSON)
  - --use-comet-ref <path> (COMET ref checkpoint)
  - --use-comet-qe <path> (COMET-QE checkpoint)
  - --lm_model <HF model name> (causal LM for fluency)
  - --sbert_model <HF model name> (sentence-transformers model)
  - --calib_json <path> (calibration mappings produced by tools/calibrate.py)

Outputs:
- out.xlf (default) — XLIFF file with chosen translations and TQE props in `prop-group`.
- Optional: log prints and per-run console output.

Installation & models
---------------------
Prereqs:
- Python 3.8+
- Git LFS (optional for some HF repos)

Recommended virtualenv setup:
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

Install core python packages (example):
```
pip install torch transformers sentence-transformers bert-score lxml tqdm rapidfuzz huggingface-hub
# COMET (optional):
pip install git+https://github.com/Unbabel/COMET.git
```

Files with dependencies:
- `tqe/requirements.txt` (append)
- Additional libs: `rapidfuzz`, `huggingface_hub`.

COMET / COMET-QE download helper
--------------------------------
We include `tools/download_comet_model.py`, which uses `huggingface_hub` to fetch a checkpoint file from an HF repo.

Example download commands (public repos):
```
python tools/download_comet_model.py --repo_id Unbabel/wmt22-comet-da --out_dir models/comet-da
python tools/download_comet_model.py --repo_id Unbabel/wmt21-comet-qe --out_dir models/comet-qe
```
Notes:
- The helper tries to pick a checkpoint-like filename (best/checkpoint). Inspect HF repo pages if you need a specific filename.
- If models are private, set `HUGGINGFACE_HUB_TOKEN` in the environment.

CLI usage & flags
-----------------
Primary script: `tqe/tqe.py`

Key flags
- --xliff <path> (required)
- --candidates <path> (required): JSON mapping { "t42": ["cand1","cand2"], "source text": [...] }
- --out <path> (default out.xlf)
- --device {cpu,cuda} (default cuda)
- --lm_model <hf-model> (optional) — e.g. `gpt2-medium` for fluency (choose target-language appropriate LM)
- --sbert_model <hf-model> (optional) — e.g. `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- COMET & QE:
  - --use-comet-ref <checkpoint_path>
  - --use-comet-qe  <checkpoint_path>
  - --comet-batch-size <int> (default 16)
  - --fp16 (use fp16 where available)
- TMX & TM fuzzy:
  - --tmx <path>
  - --fuzzy-enable (enable fuzzy TM lookup)
  - --fuzzy-threshold <float> (0..1, default 0.8)
- Terminology:
  - --terms_csv <path> (CSV termbase)
  - --terms_tbx <path> (TBX termbase)
  - --enforce-terms (strict enforcement; missing approved term => `needs_human_revision`)
  - --term-penalty <float> (soft enforcement; deduct this many points from weighted score when missing term; default 15)
  - --inject-terms-to-prompt (inject top-K relevant approved terms into the LLM prompt when generating candidates)
  - --max-terms-in-prompt <int> (default 8)
- Scoring & aggregation:
  - --weights "acc,fluency,tone" (default "0.6,0.25,0.15")
- Calibration:
  - --calib_json <path> (optional JSON to apply calibrated mappings)
- Misc:
  - --fuzzy-enable (enable fuzzy tmx matching)
  - --lang <lang_code> (target language code for BERTScore etc.)

Examples
- Strict enforcement of terms (GPU):
```
python tqe/tqe.py \
  --xliff tests/sample_input.xlf \
  --candidates tests/candidates.json \
  --tmx tests/sample.tmx \
  --terms_csv tests/terms.csv \
  --use-comet-ref models/comet-da/best_checkpoint.pt \
  --use-comet-qe models/comet-qe/best_checkpoint.pt \
  --sbert_model sentence-transformers/paraphrase-multilingual-mpnet-base-v2 \
  --device cuda --fp16 \
  --fuzzy-enable --fuzzy-threshold 0.8 \
  --enforce-terms \
  --inject-terms-to-prompt --max-terms-in-prompt 5 \
  --out tests/scored.strict.xlf
```

- Soft enforcement with 12-point penalty:
```
python tqe/tqe.py \
  --xliff tests/sample_input.xlf \
  --candidates tests/candidates.json \
  --terms_csv tests/terms.csv \
  --device cuda --fp16 \
  --term-penalty 12 \
  --out tests/scored.soft.xlf
```

Terminology integration & prompt injection
-----------------------------------------
Termbase formats:
- CSV expected columns: `source,src_lang,target,tgt_lang,approved` (variants optional)
- TBX: the included TBX parser supports a minimal subset of TBX; it will extract term entries by language.

Flow:
1. Term lookup is performed when scoring candidates:
   - Exact TMX match (exact source text match) is preferred.
   - Fuzzy TMX match (rapidfuzz Levenshtein) if no exact TMX.
   - If a term entry is available for the src->tgt pair, `match_terms_in_candidate()` computes a `term_match` score (0..100).
2. Enforcement options (user-selectable):
   - Strict (`--enforce-terms`): If `approved=True` in the termbase and the candidate does not meet a `term_match` threshold (default 50), the candidate is forced to `needs_human_revision` (overrides numeric aggregation).
   - Soft: no `--enforce-terms` and `--term-penalty X` given — if approved term missing, a fixed penalty (X points) is subtracted from the weighted score before making decisions.
3. Prompt injection into the LLM:
   - If `--inject-terms-to-prompt` is set, the top-K approved term pairs most relevant to the TU (by fuzzy match on the source) are formatted and injected into the LLM prompt during the LLM translation stage.
   - The injection helper formats a short "Term table" and brief instruction to always use these approved terms.
   - NOTE: The LLM generation stage is outside the TQE scoring module; TMXmatic should call the LLM generation with the prompt injection string. The TQE module provides the prompt text via function call or saved file (e.g., `--prompt_template` hook can be added). For local experiments you can supply the prompt to the HF model wrapper.

Fuzzy TM matching behavior
--------------------------
- Exact TM lookup first (TMX exact match for the source text).
- If no exact match and `--fuzzy-enable` is set:
  - Use `rapidfuzz.fuzz.ratio()` to compute similarity (0..100), map to [0..1].
  - If similarity >= `--fuzzy-threshold` (default 0.8), the TM match is used as a reference (human preferred).
- If multiple fuzzy matches exist, the best-scoring human-marked TM entry is chosen.
- You can tune `--fuzzy-threshold` in the UI or via the CLI.

Metric computation & aggregation logic
-------------------------------------
Per-candidate:
- Accuracy component:
  - If human reference is available (exact TMX, high fuzzy TMX, or existing XLIFF human target), prefer COMET (ref) if available.
  - Else if no ref and COMET-QE available, use COMET-QE.
  - Else fallback to BERTScore or SBERT similarity.
- Fluency:
  - Compute LM perplexity (causal LM). Lower perplexity → higher normalized score.
- Tone:
  - Compute SBERT embedding similarity between candidate and tone exemplar(s).
- Term-match:
  - Run `term_presence_score()` (0..100). This enters the meta and contributes via user-configured policy (soft penalty or strict).
- UQLM:
  - If UQLM indicates hallucination for the TU, defaults to heavy penalty: by default, the module forces `needs_human_revision`. You can tune this logic (e.g., only downweight accuracy) in code.

Aggregation:
- WeightedScore = w_acc * Accuracy + w_flu * Fluency + w_tone * Tone (defaults 0.6, 0.25, 0.15)
- Term-match integration:
  - Strict: `--enforce-terms` => missing approved term => `needs_human_revision`.
  - Soft: subtract `--term-penalty` points from WeightedScore when missing approved term.
- Decision buckets:
  - Accept auto: WeightedScore >= 85 and no UQLM hallucination, and term constraints satisfied (if strict).
  - Accept with review: 70 <= WeightedScore < 85
  - Needs human revision: WeightedScore < 70 or UQLM hallucination or strict term failure

Calibration (how-to)
--------------------
Goal: map raw model outputs (COMET scores, perplexity-derived fluency, BERTScore, SBERT sim, etc.) into an interpretable 0..100 human-aligned scale.

Tools in repo:
- `tools/calibrate.py` — fits isotonic regression mapping raw -> human. Input CSV should include columns like:
  - `tu_id`, `human_score` (0..100), `comet_raw`, `berts`, `fluency_raw`, `tone_raw`, `term_match`
- Usage:
```
python tools/calibrate.py --input calibration.csv --out calib.json
```
- Output `calib.json` contains per-metric mapping breakpoints. Provide this via `--calib_json` to `tqe/tqe.py` to apply calibrations at scoring time.

Where to get calibration data:
- WMT Metric tasks (Direct Assessment / DA) and QE datasets. WMT provides segment-level human judgments for various language pairs and domains.
- Recommended: create an in-domain sample (200–1000 segments) with human labels for accuracy/fluency/tone/term-match.

XLIFF metadata (props written)
------------------------------
The engine writes a `prop-group` in each TU containing keys prefixed with `tqe:`. Example keys:
- tqe:translation_origin — e.g., "LLM:translategemma-12b-it"
- tqe:accuracy — normalized 0..100 (float)
- tqe:accuracy.comet_ref_raw — raw COMET ref score (if used)
- tqe:accuracy.comet_qe_raw — raw COMET-QE score (if used)
- tqe:fluency — normalized 0..100
- tqe:fluency_model — model id used
- tqe:tone — normalized 0..100
- tqe:term_match — 0..100
- tqe:term_method — 'exact','fuzzy','compound','none'
- tqe:weighted_score — aggregated score 0..100
- tqe:decision — one of `accept_auto`, `accept_with_review`, `needs_human_revision`
- tqe:uqm_hallucination — boolean
- tqe:models_used — JSON string with per-metric model names / raw component values
- tqe:timestamp — ISO timestamp when scoring performed

These props allow downstream tools to show both raw model outputs and the final decision.

Integration with TMXmatic UI
----------------------------
Map these CLI flags / options into TMXmatic UI controls:

Model & runtime:
- Model device selection: CPU / GPU (maps to `--device`)
- Enable FP16 toggle => `--fp16` (only use when GPU & supported)

COMET & QE:
- COMET ref model path picker => `--use-comet-ref`
- COMET-QE path => `--use-comet-qe`
- COMET batch size => `--comet-batch-size`

TMX / TM:
- TMX upload / select => `--tmx`
- Fuzzy matching toggle + fuzzy threshold slider => `--fuzzy-enable` and `--fuzzy-threshold`

Terminology:
- Upload termbase (CSV/TBX) => `--terms_csv` / `--terms_tbx`
- Enforcement mode selection (radio):
  - Strict => `--enforce-terms` on
  - Soft => `--term-penalty <N>` (user sets penalty)
- Prompt injection toggle => `--inject-terms-to-prompt`, `--max-terms-in-prompt` numeric

Calibration:
- Upload `calib.json` => `--calib_json` toggle
- Buttons to run calibration workflow (calls `tools/calibrate.py` with provided human-labeled CSV)

Other UI considerations:
- Show per-TU metadata in a QA panel (display all `tqe:*` props and the reasoning summary)
- Flag TUs that are `needs_human_revision` or where strict term enforcement failed
- Allow re-scoring after user changes weights or enforcement policy (expose weights editing)

Testing (synthetic dataset)
---------------------------
A small synthetic test is included in `tests/`:
- `tests/sample_input.xlf` — small XLIFF with two TUs
- `tests/candidates.json` — two candidate lists for TUs
- `tests/sample.tmx` — one TMX entry that matches TU1
- `tests/terms.csv` — a CSV termbase with approved terms

Run (GPU):
```
python tqe/tqe.py \
  --xliff tests/sample_input.xlf \
  --candidates tests/candidates.json \
  --tmx tests/sample.tmx \
  --terms_csv tests/terms.csv \
  --sbert_model sentence-transformers/paraphrase-multilingual-mpnet-base-v2 \
  --device cuda --fp16 \
  --fuzzy-enable --fuzzy-threshold 0.8 \
  --enforce-terms \
  --inject-terms-to-prompt \
  --out tests/scored.xlf
```

Or without COMET (fast smoke test):
```
python tqe/tqe.py --xliff tests/sample_input.xlf --candidates tests/candidates.json --terms_csv tests/terms.csv --out tests/scored.nocomet.xlf
```

Performance & GPU tuning (RTX 12GB)
----------------------------------
- RTX 12 GB is enough for SBERT and medium causal LMs with moderate batch sizes, and for many COMET checkpoints — but memory usage depends on COMET model size.
- Recommended settings for RTX 12GB:
  - Use `--fp16` where supported by models.
  - COMET batch size: 8–12 (use `--comet-batch-size 8` if OOM occurs)
  - LM batch size (implicit): keep small (1–4) for long segments.
  - Monitor `nvidia-smi` and reduce batch sizes / disable fp16 if model wrappers do not support half precision.
- Note: COMET uses PyTorch Lightning under the hood; moving to half precision may need extra handling for the dataloader / PL trainer. The prototype attempts `.half()` safely but watch for warnings.

Troubleshooting
---------------
- COMET import errors:
  - Ensure `git+https://github.com/Unbabel/COMET.git` is installed.
  - If `load_from_checkpoint` fails, check the checkpoint path and the HF repo file structure.
- HuggingFace download errors:
  - Set `HUGGINGFACE_HUB_TOKEN` if models are gated.
  - Install `git-lfs` if you want to `git clone` model repos (helper uses `hf_hub_download` and avoids manual git-lfs).
- Rapidfuzz not installed:
  - `pip install rapidfuzz` — fuzzy matching disabled otherwise.
- Memory OOM:
  - Lower `--comet-batch-size`, disable fp16, or run on a larger GPU.
- Inconsistent scoring ranges:
  - Use calibration (`tools/calibrate.py`) with a small human-labeled set to align raw->0..100.

References & datasets
---------------------
- COMET docs / model hub: https://unbabel.github.io/COMET/
- Unbabel HF models (examples): `Unbabel/wmt22-comet-da`, `Unbabel/wmt21-comet-qe`
- WMT Metric Shared Tasks (DA) and QE tasks for calibration and datasets:
  - https://www.statmt.org/
  - Search for year-specific pages: "WMT 2021 QE", "WMT22 metrics"
- TBX and termbase resources:
  - TBX specification: https://www.gala-global.org/tbx

Files included in this module
-----------------------------
- `tqe/tqe.py` — main scoring engine (CLI)
- `tqe/terminology.py` — termbase helpers (CSV/TBX loading and matching)
- `tools/download_comet_model.py` — helper to fetch COMET checkpoints from HF
- `tools/calibrate.py` — isotonic regression calibration helper
- `tests/` — sample `sample_input.xlf`, `candidates.json`, `sample.tmx`, `terms.csv`
- `tqe/requirements.txt` — additional python dependencies to append

Developer notes / extension points
----------------------------------
- UI: expose enforcement policy toggle and slider for `--term-penalty`, as well as `--fuzzy-threshold` and aggregation weights.
- LLM prompt injection: the module provides the prompt snippet; the LLM-generation step in TMXmatic should accept an injected prompt. This keeps generation & scoring decoupled.
- TMX fuzzy matching: you can further enhance fuzzy matching by using token-based similarity or language-specific normalization (deaccenting, collating).
- Compound handling: for German/compound-rich languages, consider integrating language-specific compound splitters or morphological analyzers (e.g., Python packages for German compounding).
- Ensemble: when both COMET and other metrics are available, you may ensemble them (e.g., average COMET and BERTScore) before applying calibration.

Questions / next steps
----------------------
I can:
- Add a prompt template helper (file-based) and example injection code for `google/translategemma-12b` usage in TMXmatic's LLM step.
- Create a small GUI mock mapping UI toggles to CLI flags for the TMXmatic devs.
- Add unit tests for term matching (compound cases) if you want stronger coverage.

If you want me to include the prompt injection helper and an example prompt template file now, say "include prompt template and injection helper" and I will add it to the repo.

Thank you — if everything looks good I can prepare a PR patch set (files already shown in `tqe/` and `tools/`) and a short `CHANGELOG` entry describing the TQE addition for the TMXmatic repo.