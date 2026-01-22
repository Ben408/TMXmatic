# Resolved Decisions & Implementation Details

## Summary of Key Decisions

This document consolidates all resolved questions and decisions made during the planning phase for the LLM Quality Module.

---

## Critical Resolutions ✅

### 1. UQLM Integration
- **Repository**: https://github.com/cvs-health/uqlm
- **Installation**: Pull from GitHub repo on demand (don't bundle)
- **Method**: Install via pip: `pip install uqlm`
- **Documentation**: https://cvs-health.github.io/uqlm/latest/index.html
- **Integration**: Use Python package interface, supports multiple scorer types (black-box, white-box, ensemble, LLM-as-judge)

### 2. translategemma Model
- **Model ID**: `google/translategemma-12b-it`
- **HuggingFace**: https://huggingface.co/google/translategemma-12b-it/tree/main
- **Quantization**: Support INT8/INT4 for 8GB/12GB GPUs; research GGUF format
- **Download**: On first use, check if present, download if not
- **Storage**: `{TMXmatic_install_dir}/models/`

### 3. XLIFF Metadata & Match Rates ✅ RESOLVED
- **Critical Decision**: Do NOT use custom props - maximize compatibility with standard XLIFF formats
- **XLIFF 1.2 Format**: 
  - Use `<alt-trans>` element with `match-quality="XX%"` attribute (percentage string)
  - Use `state-qualifier` attribute on `<target>` for match types: `exact-match`, `fuzzy-match`, `leveraged-tm`
  - Use `extype` attribute on `<alt-trans>` to specify match source (tm, mt, llm, etc.)
- **XLIFF 2.0/2.1/2.2 Format**: 
  - Use Translation Candidates module: namespace `urn:oasis:names:tc:xliff:matches:2.0` (prefix: `mtc`)
  - Use `<mtc:matches>` containing `<mtc:match>` elements with attributes:
    - `similarity` (0.0-100.0): Source text similarity
    - `matchQuality` (0.0-100.0): Translation quality from TQE scoring
    - `matchSuitability` (0.0-100.0): Combined metric for ranking (weighted combination)
    - `type`/`origin`: Match source type (tm, mt, tb, llm, etc.)
- **Match Suitability Calculation**: `matchSuitability = 0.5 * similarity + 0.5 * matchQuality` (user-configurable weights)
- **Thresholds**: 
  - Exact match: ≥95% matchSuitability and similarity=100%
  - Fuzzy match: 75-94.99% matchSuitability
  - Low quality/No match: <75% matchSuitability (flagged with quality note)
- **Quality Warnings**: Use standard `<note>` elements with `category="quality"`
  - Format: `<note category="quality">Quality warning: Low accuracy score (45/100)</note>`
- **Target Platforms**: Trados Studio, Phrase TMS, Crowdin, Trados Enterprise (all support these standard formats)

### 4. Configuration Profiles
- **Storage Location**: `{TMXmatic_install_dir}/config/profiles/`
- **Format**: JSON or YAML per profile
- **Support**: Multiple profiles per installation (different organizations/clients)
- **Scope**: Per-user initially, consider user-specific subdirectories for multi-user

### 5. Language Pair Handling
- **Decision**: Auto-detect all language pairs, process all pairs
- **Implementation**: Parse XLIFF headers, identify all source-target pairs, process each
- **Profile Support**: One profile can support multiple language pairs

### 6. Term Injection Format
- **Format**: Simple list format (unless testing reveals better practices)
- **Example**: "Use these approved terms: term1→translation1, term2→translation2"
- **Scope**: Extract terms from TBX/CSV only for segments needing LLM translation
- **Multiple Termbases**: Limit to one termbase initially (TBX or CSV), future enhancement if needed

### 7. Error Handling & Fail-Fast
- **Single Segment Failure**: Log only, continue processing
- **Systematic Failure**: Consecutive failures trigger fail-fast
  - Default threshold: 5 consecutive failures (configurable)
- **Partial Results**: Always save partial results before failing
- **Retry Logic**: Retry transient errors (GPU OOM, model load failures)

### 8. Progress Tracking
- **Method**: Polling + Server-Sent Events (SSE)
- **Primary**: SSE for real-time push updates
- **Fallback**: Polling if SSE not supported
- **Update Frequency**: Every 10 segments or 5 seconds (whichever comes first)

### 9. Model Management
- **Updates**: Manual process from model manager screen
- **UI**: "Check for Updates" button triggers version check
- **Behavior**: Show available updates, user initiates download
- **Versioning**: Store model versions, allow downgrade if needed

### 10. Batch Size Configuration
- **Approach**: Both auto-tune and manual override
- **Default**: Auto-tune based on GPU memory and segment length
- **Override**: User-configurable per profile in config settings
- **Fallback**: If auto-tune fails, prompt user to set manually

---

## Architecture Decisions

### Module Separation
- **LLM Translation**: Separate module (`llm_translation/`)
  - Handles translation generation, term injection, candidate creation
- **TQE Scoring**: Enhanced existing module (`tqe/`)
  - Quality estimation, terminology validation, UQLM integration
- **Workflow Orchestration**: New module (`integration/`)
  - Coordinates assets, routes to appropriate workflows

### Workflow Logic
1. **XLIFF Only**: Minimal processing → Translate missing segments
2. **XLIFF + TMX**: Match TMX first → Skip LLM for exact matches → Translate remaining
3. **XLIFF + TMX + TBX**: Full workflow → Extract terms → Inject into prompts → Validate term usage

### TMX Matching Priority
1. Exact match → Use TMX target, skip LLM
2. High fuzzy match (≥threshold) → Use TMX target, skip LLM
3. Low fuzzy match (<threshold) → Generate LLM candidates, score against fuzzy match
4. No match → Generate LLM candidates

---

## Technical Specifications

### GPU Support
- **Target GPUs**: RTX 8GB, 12GB, 16GB
- **Detection**: Auto-detect capability, warn and fail gracefully if unavailable
- **Memory Management**: 
  - 8GB: Use 4-bit quantization, batch size 1-2
  - 12GB: Use 8-bit quantization, batch size 4-8
  - 16GB: Use 8-bit or 16-bit, batch size 8-16

### Model Sizes (Estimated)
- translategemma-12b: ~24GB (FP16), ~12GB (INT8), ~6GB (INT4)
- COMET models: ~1-2GB each
- UQLM: Python package, minimal disk space

### Processing Strategy
- **Chunked Processing**: Process XLIFF in chunks of 100 segments
- **Checkpointing**: Save partial results every 50 segments
- **Progress Updates**: Update every 10 segments or 5 seconds

---

## Remaining Research Items

### High Priority

1. **XLIFF Match Rate Prop Format**
   - Research standard XLIFF prop types for match rates
   - Verify compatibility: Trados Studio, Phrase TMS, Crowdin, Trados Enterprise
   - Determine: XLIFF 2.0 `match-percentage` prop vs XLIFF 1.2 `match-quality` attribute
   - **Timeline**: Complete before Phase 3 (XLIFF Integration)

2. **translategemma Quantization Testing**
   - Test different quantization formats (GGUF, INT8, INT4)
   - Benchmark quality vs speed tradeoffs
   - Determine optimal quantization per GPU tier
   - **Timeline**: Complete during Phase 1 (Foundation)

### Medium Priority

3. **Quality Threshold Defaults**
   - Determine specific numeric thresholds through testing
   - Decide on weighted score vs UQLM confidence combination
   - **Timeline**: Determine during Phase 2 (TQE Integration)

4. **Term Injection Prompt Optimization**
   - Test simple list format vs structured formats
   - Optimize for translategemma performance
   - **Timeline**: Refine during Phase 1-2 development

---

## Implementation Priorities

### Phase 1 (Weeks 1-3): Foundation
1. GPU detection and graceful fallback
2. Model management (download, cache, version control)
3. LLM translation module with basic term injection
4. TMX matching logic

### Phase 2 (Weeks 4-5): Quality Estimation
1. TQE scoring integration
2. UQLM integration
3. Terminology validation
4. Scoring aggregation

### Phase 3 (Weeks 6-7): XLIFF Integration
1. XLIFF processing with metadata preservation
2. Standard metadata writing (match rates, quality flags)
3. Note elements for quality warnings
4. **Research match rate prop format before this phase**

### Phase 4 (Week 8): Configuration
1. Profile management system
2. Multi-profile support
3. Configuration UI

### Phase 5-8 (Weeks 9-14): Integration & Polish
1. Flask API endpoints
2. UI components
3. Error handling and logging
4. Installer and packaging

---

## Notes

- All decisions prioritize **compatibility** and **standard compliance** over custom solutions
- User preference is to avoid custom props/namespaces entirely
- Focus on broad TMS platform compatibility (Trados, Phrase, Crowdin)
- Conservative approach: one termbase initially, expand if needed
- Manual processes preferred over automation (model updates, configuration)

---

## References

- UQLM: https://github.com/cvs-health/uqlm
- UQLM Docs: https://cvs-health.github.io/uqlm/latest/index.html
- translategemma: https://huggingface.co/google/translategemma-12b-it/tree/main
- XLIFF 1.2 Specification: https://docs.oasis-open.org/xliff/v1.2/cs02/xliff-core.html
- XLIFF 2.0 Specification: https://docs.oasis-open.org/xliff/xliff-core/v2.0/csprd02/xliff-core-v2.0-csprd02.html
- XLIFF 2.2 Translation Candidates Module: https://docs.oasis-open.org/xliff/xliff-core/v2.2/xliff-extended-v2.2-part2.html
- Translation Candidates Module Namespace: `urn:oasis:names:tc:xliff:matches:2.0`

---

*Last Updated: Based on planning session decisions and XLIFF standard research*
