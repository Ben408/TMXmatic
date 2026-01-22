# TQE Module (Translation Quality Estimation)

**Location**: `shared/tqe/`  
**Status**: ✅ Integrated with LLM Quality Module for TMXmatic  
**Version**: 2.0 (Refactored for shared infrastructure)

---

## Overview

The Translation Quality Estimation (TQE) module evaluates candidate translations from LLMs and selects the best candidate based on multiple quality metrics. It is now part of the **LLM Quality Module for TMXmatic** and integrated with shared infrastructure for model management, GPU detection, and configuration.

### Key Features
- **Multi-metric scoring**: Accuracy, fluency, tone, term-match, hallucination detection
- **Reference-based quality**: COMET (with reference) or COMET-QE (without reference)
- **Terminology validation**: TBX/CSV termbase integration with strict/soft enforcement
- **TMX integration**: Exact and fuzzy matching with translation memory
- **XLIFF metadata**: Standard format support (1.2 and 2.0+) for TMS compatibility
- **Shared infrastructure**: Integrated with model manager, GPU detector, profile manager

---

## Architecture

### Module Structure
```
shared/tqe/
├── tqe.py              # Main TQE engine
├── scoring.py          # Scoring primitives (accuracy, fluency, tone)
├── xliff_utils.py      # XLIFF parsing and writing
├── tmx_utils.py        # TMX parsing and fuzzy matching
├── terminology.py      # Termbase loading and matching
├── comet_utils.py      # COMET model utilities
└── uqlm_integration.py # UQLM hallucination detection
```

### Integration Points
- **Model Management**: Uses `shared/models/model_manager.py` for model downloading/caching
- **GPU Detection**: Uses `shared/gpu/detector.py` for GPU capability checking
- **Configuration**: Uses `shared/config/profile_manager.py` for user profiles
- **Error Handling**: Uses `shared/utils/error_recovery.py` for retry logic
- **Logging**: Uses `shared/utils/logging.py` for consistent logging

---

## Usage

### Python API

```python
from shared.tqe.tqe import TQEEngine
from shared.models.model_manager import ModelManager
from shared.models.memory_manager import MemoryManager

# Initialize
model_manager = ModelManager()
memory_manager = MemoryManager()
tqe_engine = TQEEngine(
    device="cuda",
    lm_name="gpt2-medium",  # Optional: for fluency
    sbert_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    comet_ref_ckpt="path/to/comet-ref.pt",  # Optional
    comet_qe_ckpt="path/to/comet-qe.pt",    # Optional
    fp16=True
)

# Score XLIFF
candidates = {
    "tu1": ["Translation 1", "Translation 2"],
    "tu2": ["Translation A", "Translation B"]
}

tqe_engine.score_xliff(
    xliff_path="input.xlf",
    candidates=candidates,
    tmx_map=tmx_map,  # Optional: from shared.tqe.tmx_utils.parse_tmx()
    uqlm_map=uqlm_map,  # Optional: pre-computed UQLM results
    tone_exemplars_map=tone_exemplars,  # Optional
    out_path="output.xlf",
    weights=(0.6, 0.25, 0.15),  # accuracy, fluency, tone
    lang="en",
    fuzzy_threshold=0.8,
    fuzzy_enable=True
)
```

### Command Line (Legacy)

The original CLI interface in `tqe/tqe.py` is still available for standalone use, but the recommended approach is to use the integrated workflow through `local_gpu_translation/main.py` or the Flask API.

---

## Scoring Metrics

### Accuracy (0-100)
- **With reference**: COMET (reference-based) > BERTScore > SBERT similarity
- **Without reference**: COMET-QE > SBERT similarity
- **Reference sources** (priority order):
  1. Exact TMX match
  2. High fuzzy TMX match (≥threshold)
  3. Existing XLIFF target marked as human

### Fluency (0-100)
- Language model perplexity → normalized score
- Lower perplexity = higher fluency score
- Requires causal LM model (optional)

### Tone (0-100)
- SBERT embedding similarity to tone exemplars
- Average similarity across exemplar set
- Requires SBERT model (default: multilingual MPNet)

### Term Match (0-100)
- Validates approved terminology usage
- Checks for exact/fuzzy term matches in candidate
- Integrated into weighted score with penalty or strict enforcement

### Hallucination Detection
- UQLM integration for factuality checking
- Heavy penalty applied when hallucination detected
- Forces `needs_human_revision` decision

---

## Score Aggregation

### Weighted Score
```
WeightedScore = w_acc * Accuracy + w_flu * Fluency + w_tone * Tone
```

Default weights: `(0.6, 0.25, 0.15)` for accuracy, fluency, tone

### Decision Buckets
- **Accept Auto**: WeightedScore ≥ 85, no hallucination, terms satisfied
- **Accept with Review**: 70 ≤ WeightedScore < 85
- **Needs Human Revision**: WeightedScore < 70, or hallucination, or strict term failure

### Term Enforcement
- **Strict**: Missing approved term → `needs_human_revision`
- **Soft**: Missing approved term → penalty (default 15 points) subtracted from weighted score

---

## XLIFF Metadata

### Standard Format Support

The module writes quality metadata using **standard XLIFF formats** for maximum TMS compatibility (Trados Studio, Phrase TMS, Crowdin, etc.).

#### XLIFF 1.2
- `<alt-trans>` with `match-quality` attribute (0-1 range)
- `state-qualifier` on `<target>`: `exact-match`, `fuzzy-match`, `low-match`
- `<note>` elements with `category="quality"` for warnings

#### XLIFF 2.0+
- Translation Candidates module (`mtc:match`)
- `similarity` (0-1): Source similarity
- `matchQuality` (0-100): TQE weighted score
- `matchSuitability` (0-100): Combined metric
- `type` and `origin` attributes

### Internal Metadata
Detailed scoring information in `<note>` elements:
- `tqe:accuracy` - Accuracy score
- `tqe:fluency` - Fluency score
- `tqe:tone` - Tone score
- `tqe:weighted_score` - Aggregate score
- `tqe:decision` - Decision bucket
- `tqe:uqm_hallucination` - Hallucination flag
- `tqe:timestamp` - Processing timestamp

---

## Integration with LLM Quality Module

### Workflow Integration

The TQE engine is integrated into the translation workflow:

1. **Translation**: LLM generates N-best candidates
2. **TMX Matching**: Exact/fuzzy matches identified
3. **TQE Scoring**: All candidates scored
4. **Selection**: Best candidate chosen
5. **Metadata**: Scores and match rates written to XLIFF

### API Integration

The TQE engine is used automatically in the translation workflow:

```python
from local_gpu_translation.integration.workflow_manager import WorkflowManager
from local_gpu_translation.llm_translation.translator import Translator
from shared.tqe.tqe import TQEEngine

# TQE engine is integrated into workflow
workflow_manager = WorkflowManager(translator, tqe_engine)
workflow_manager.process_xliff(xliff_path, output_path, src_lang, tgt_lang)
```

---

## Models

### Required Models
- **SBERT**: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (0.4GB)
  - Used for: Tone scoring, similarity calculations
  - Auto-downloaded on first use

### Optional Models
- **COMET Reference**: `Unbabel/wmt22-comet-da` (0.5GB)
  - Used for: Reference-based accuracy scoring
- **COMET-QE**: `Unbabel/wmt22-cometkiwi-da` (0.5GB)
  - Used for: Quality estimation without reference
- **Causal LM**: Any HuggingFace causal LM (varies)
  - Used for: Fluency scoring via perplexity

### Model Management
Models are managed through `shared/models/model_manager.py`:
- Automatic downloading from HuggingFace
- Caching and versioning
- Path resolution

---

## Configuration

### Profile-Based Settings

TQE settings can be configured per profile:

```json
{
  "tqe_weights": {
    "accuracy": 0.6,
    "fluency": 0.25,
    "tone": 0.15,
    "term_match": 0.1
  },
  "thresholds": {
    "accept_auto": 85,
    "accept_with_review": 70,
    "fuzzy_tmx_threshold": 0.8
  },
  "enforcement_policy": "soft",
  "term_penalty": 15
}
```

### Global Fallback
If profile settings not available, global defaults are used.

---

## Testing

### Unit Tests
- **Location**: `tests/unit/shared/test_tqe/`
- **Coverage**: 36-92% (varies by component)
- **Test Files**:
  - `test_scoring.py` - Scoring functions
  - `test_xliff_utils.py` - XLIFF utilities
  - `test_tmx_utils.py` - TMX utilities

### Integration Tests
- **Location**: `tests/integration/test_workflows/`
- Tests end-to-end workflow with TQE integration

### Running Tests
```bash
# Unit tests
pytest tests/unit/shared/test_tqe/ -v

# All tests
pytest tests/ -v
```

---

## Performance

### GPU Requirements
- **RTX 8GB**: SBERT, small COMET models
- **RTX 12GB**: Recommended for full feature set
- **RTX 16GB+**: Optimal for large batches

### Optimization
- Use `fp16=True` for GPU models (when supported)
- Adjust `comet_batch` size based on GPU memory
- Batch processing for large XLIFF files

---

## Troubleshooting

### Common Issues

**COMET import errors**:
- Install: `pip install git+https://github.com/Unbabel/COMET.git`

**Model download failures**:
- Check HuggingFace token: `HUGGINGFACE_HUB_TOKEN`
- Verify internet connection
- Check disk space

**GPU OOM errors**:
- Reduce `comet_batch` size
- Disable `fp16` if not supported
- Use CPU fallback

**Low coverage scores**:
- Verify reference quality (TMX matches)
- Check termbase relevance
- Consider calibration (see below)

---

## Calibration

For domain-specific calibration:

1. Create calibration dataset with human scores
2. Run `tools/calibrate.py` to generate calibration mappings
3. Apply calibration in TQE engine (future enhancement)

---

## Migration from Standalone TQE

If migrating from the standalone `tqe/tqe.py`:

### Changes
- ✅ TQE code moved to `shared/tqe/`
- ✅ Integrated with shared infrastructure
- ✅ Model management via `ModelManager`
- ✅ Profile-based configuration
- ✅ Enhanced error handling

### Compatibility
- Original CLI interface still available in `tqe/tqe.py`
- API remains similar, with additional integration options
- XLIFF output format unchanged

---

## Files

### Core Module
- `shared/tqe/tqe.py` - Main TQE engine
- `shared/tqe/scoring.py` - Scoring primitives
- `shared/tqe/xliff_utils.py` - XLIFF utilities
- `shared/tqe/tmx_utils.py` - TMX utilities
- `shared/tqe/terminology.py` - Terminology utilities
- `shared/tqe/comet_utils.py` - COMET integration
- `shared/tqe/uqlm_integration.py` - UQLM integration

### Legacy (Still Available)
- `tqe/tqe.py` - Original CLI interface
- `tqe/terminology.py` - Original terminology module

### Tools
- `tools/calibrate.py` - Calibration helper
- `tools/download_comet_model.py` - COMET download helper

---

## References

- **COMET**: https://unbabel.github.io/COMET/
- **UQLM**: https://github.com/cvs-health/uqlm
- **XLIFF Specification**: https://docs.oasis-open.org/xliff/xliff-core/v2.1/os/xliff-core-v2.1-os.html
- **TMX Specification**: https://www.gala-global.org/tmx
- **TBX Specification**: https://www.gala-global.org/tbx

---

## Status

✅ **Integrated and Tested**
- Part of LLM Quality Module for TMXmatic
- 20 unit tests passing
- Integrated with shared infrastructure
- Ready for production use

---

**Last Updated**: 2025-01-XX  
**Module Version**: 2.0  
**Integration Status**: Complete
