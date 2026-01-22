# LLM Quality Module for TMXmatic - Implementation Plan

## Overview
This module provides local GPU-powered translation and quality estimation capabilities for TMXmatic. It allows engineers with RTX 8GB, 12GB, or 16GB GPUs to perform translation and quality assessment locally without relying on cloud services.

**Repository**: https://github.com/Ben408/TMXmatic  
**Target Branch**: `Local_translate_QA`  
**Status**: In Development

## Integration Context

### Related Work in Progress
- **Dynamic Dependencies**: ✅ Already implemented - module can leverage existing dependency management
- **Auth & User Management**: 🔄 Underway by different engineer - plan for integration points
- **Okapi Integration**: 🔄 Underway by different engineer - separate from this module
- **Multi-Agent System**: 📋 Planned - uses serverless LLMs (RunPod/HF), different from local GPU module

### Architecture Alignment
- **Option B Selected**: Shared Infrastructure, Separate Modules
- This module focuses on **local GPU-based** translation and QA
- Multi-agent system will use **serverless LLM endpoints** (complementary, not competing)
- **Shared Infrastructure**: Model management, GPU management, TQE scoring, configuration management
- Both systems will use the same shared infrastructure layer
- Multi-agent system can be built later using shared components without duplication
- This approach maximizes code reuse while maintaining clear module boundaries

## Core Requirements Summary

### Functional Requirements
1. **Separate LLM translation module** that handles:
   - XLIFF only → minimal processing, translate missing segments
   - XLIFF + TMX → match TMX first, then handle remaining segments
   - XLIFF + TMX + TBX → inject terms into prompts, validate term usage

2. **TMX matching strategy**:
   - Exact TMX match → Use TMX translation, skip LLM
   - High fuzzy TMX match → Use LLM to repair/improve the fuzzy match translation
   - No match → Generate new translation via LLM

3. **Term extraction and injection** only for segments needing LLM translation (not for human-approved translations)

4. **Multi-asset workflow** that adapts based on available inputs

5. **Comprehensive metadata** written to XLIFF TUs including:
   - Translation origin (TMX match, LLM, etc.)
   - Quality scores (accuracy, fluency, tone, term-match)
   - Aggregate match rate for TMS compatibility (XLIFF 1.2-2.2)
   - Quality flags and warnings

6. **Error handling**:
   - Single segment failures → log only
   - Systematic failures → fail fast with partial results saved
   - Retry transient errors (GPU OOM, model load failures)

7. **Configuration profiles**:
   - Per-user settings
   - Multiple profile support (different organizations/clients)
   - Persistent storage

### Technical Requirements
- **GPU Detection**: Auto-detect GPU capability, warn and fail gracefully if unavailable
- **Model Management**: Download, cache, version control for all models
- **Language Agnostic**: Auto-detect language pairs from XLIFF/TMX headers
- **Conservative Batching**: Handle large files efficiently with chunked processing
- **Progress Tracking**: Real-time progress updates via polling or websockets

---

## Architecture

### Shared Infrastructure + Local GPU Module Structure

**Option B Architecture**: Shared infrastructure layer used by both Local GPU Module and future Multi-Agent System.

```
TMXmatic/ (root)
│
├── shared/                    # ✅ SHARED INFRASTRUCTURE (built first)
│   ├── __init__.py
│   ├── models/               # Shared model management
│   │   ├── __init__.py
│   │   ├── model_manager.py  # Download, cache, version control (all models)
│   │   ├── gpu_detector.py   # GPU capability detection
│   │   └── memory_manager.py # GPU memory management and optimization
│   │
│   ├── gpu/                  # Shared GPU utilities
│   │   ├── __init__.py
│   │   ├── detector.py       # GPU detection utilities
│   │   └── memory.py         # Memory management utilities
│   │
│   ├── config/               # Shared configuration management
│   │   ├── __init__.py
│   │   ├── profile_manager.py # Multi-profile configuration (user-specific)
│   │   ├── prompt_manager.py  # Prompt template management (externalized)
│   │   ├── default_settings.json
│   │   └── schema.py         # Configuration validation
│   │
│   ├── tqe/                  # ✅ Shared TQE scoring engine
│   │   ├── __init__.py
│   │   ├── tqe.py            # Main scoring engine (enhanced, reusable)
│   │   ├── terminology.py    # Term matching and validation
│   │   └── uqlm_integration.py # UQLM hallucination detection
│   │
│   └── utils/                # Shared utilities
│       ├── __init__.py
│       ├── logging.py        # Logging utilities
│       └── error_recovery.py # Error recovery patterns
│
├── local_gpu_translation/     # Local GPU Translation Module
│   ├── __init__.py
│   ├── llm_translation/      # LLM translation generation
│   │   ├── __init__.py
│   │   ├── translator.py     # Main translation orchestrator
│   │   ├── candidate_generator.py # N-best generation with term injection
│   │   ├── term_extractor.py # Extract terms from TBX/TMX
│   │   └── prompt_builder.py # Build prompts from templates (uses shared/prompts)
│   │
│   ├── integration/          # Workflow orchestration
│   │   ├── __init__.py
│   │   ├── workflow_manager.py # Orchestrates based on available assets
│   │   ├── tmx_matcher.py    # TMX matching logic (exact/fuzzy)
│   │   └── asset_coordinator.py # Coordinates XLIFF, TMX, TBX inputs
│   │
│   ├── io/                   # File I/O and XLIFF handling
│   │   ├── __init__.py
│   │   ├── xliff_processor.py # XLIFF read/write with metadata preservation
│   │   ├── tmx_parser.py     # Enhanced TMX parsing for matching
│   │   ├── tbx_parser.py     # TBX parsing for terminology
│   │   └── metadata_writer.py # Write TQE metadata and match rates to XLIFF
│   │
│   ├── api/                  # Flask API integration
│   │   ├── __init__.py
│   │   ├── endpoints.py      # Flask endpoints for translation + TQE
│   │   ├── progress_tracker.py # Progress tracking (reuses existing pattern)
│   │   └── error_handler.py  # API error handling
│   │
│   └── installer/            # Module-specific installer
│       ├── __init__.py
│       └── installer.py      # Installer for local GPU module
│
├── ui/                       # UI components (Next.js integration)
│   ├── local_gpu/            # Local GPU module UI components
│   │   ├── translation_panel.tsx # Translation operation panel
│   │   ├── model_manager_panel.tsx # Model management (uses shared models)
│   │   ├── config_profile_editor.tsx # Profile editor (uses shared config)
│   │   ├── prompt_editor.tsx # Prompt template editor
│   │   └── quality_dashboard.tsx # Quality metrics visualization
│   │
│   └── shared/               # Shared UI components (if any)
│
├── config/                   # Configuration storage
│   ├── profiles/             # User-specific profiles
│   │   ├── {user_id}/        # Per-user profiles (with auth)
│   │   └── global/           # Global profiles (without auth)
│   ├── prompts/              # Prompt templates
│   │   ├── prompt_templates.ini # Externalized prompts
│   │   └── default/          # Default prompt templates
│   └── global_settings.json  # Global default settings
│
├── models/                   # Shared model storage
│   └── {model_name}/         # Model files (shared across all users)
│
└── tests/                    # Test suite
    ├── shared/               # Tests for shared infrastructure
    ├── local_gpu/            # Tests for local GPU module
    └── integration/          # Integration tests
```

### Key Architecture Decisions (Option B)

1. **Shared Infrastructure First**: Build reusable components that both modules can use
2. **Clean Interfaces**: Shared modules expose clean APIs for reuse
3. **No Tight Coupling**: Local GPU module and future Multi-Agent system remain independent
4. **Code Reuse**: Model management, GPU detection, TQE scoring, config management all shared
5. **Independent Development**: Each module can be developed separately after shared foundation

---

## Implementation Phases

### Phase 0: Shared Infrastructure Foundation (Week 1) ✅ NEW

**Objective**: Build shared infrastructure components that both Local GPU Module and Multi-Agent System will use.

#### 0.1 Shared Model Management
- [ ] Implement `shared/models/model_manager.py`:
  - Download models from HuggingFace (translategemma, COMET, etc.)
  - Model caching and version control
  - Support for multiple model types (LLM, COMET, SBERT, etc.)
  - Shared storage location: `{install_dir}/models/` (all users)
  
- [ ] Implement `shared/models/gpu_detector.py`:
  - Auto-detect CUDA-capable GPU
  - Detect GPU memory (8GB/12GB/16GB)
  - Warn if no GPU available
  - Fail gracefully with clear error messages
  
- [ ] Implement `shared/models/memory_manager.py`:
  - Monitor GPU memory usage
  - Dynamic batch size adjustment
  - Model loading/unloading coordination
  - Keep models loaded for performance (confirmed requirement)

#### 0.2 Shared Configuration Management
- [ ] Implement `shared/config/profile_manager.py`:
  - User-specific profile support
  - Profile storage: `{install_dir}/config/profiles/{user_id}/` (with auth)
  - Global profiles: `{install_dir}/config/profiles/global/` (without auth)
  - Profile CRUD operations
  - Global fallback for missing profile settings
  
- [ ] Implement `shared/config/prompt_manager.py`:
  - Externalized prompt template management (INI format)
  - Default prompt templates included
  - User-editable prompts via config files
  - Prompt template validation
  - Templates stored in: `{install_dir}/config/prompts/prompt_templates.ini`
  - Reference: Sage Local `Process_Variants/config.ini` pattern

#### 0.3 Shared TQE Engine
- [ ] Enhance existing `shared/tqe/tqe.py` (move from current location):
  - Make it a reusable, standalone module
  - Clean interfaces for scoring candidates
  - Support both local GPU and serverless LLM workflows
  - No tight coupling to specific implementation
  
- [ ] Implement `shared/tqe/uqlm_integration.py`:
  - Pull UQLM from GitHub repo (cvs-health/uqlm)
  - Integrate hallucination detection
  - Reusable by both Local GPU and Multi-Agent systems

#### 0.4 Shared Utilities
- [ ] Implement `shared/utils/logging.py`:
  - Logging utilities aligned with TMXmatic
  - Consistent logging patterns
  
- [ ] Implement `shared/utils/error_recovery.py`:
  - Common error recovery patterns
  - Retry logic utilities

**Deliverables**:
- ✅ Shared model management (download, cache, GPU detection)
- ✅ Shared configuration system (profiles, prompts)
- ✅ Shared TQE scoring engine (reusable interfaces)
- ✅ Shared utilities (logging, error recovery)
- ✅ Clean APIs for future module reuse

---

### Phase 1: Foundation & Core Translation (Weeks 2-4)

#### 1.1 Local GPU Module Integration with Shared Infrastructure
- [ ] Use `shared/models/model_manager.py` (built in Phase 0):
  - Download translategemma-12b-it (quantized GGUF format)
  - Download COMET, COMET-QE models
  - Model versioning and caching (already implemented in shared)
  
- [ ] Use `shared/models/gpu_detector.py` (built in Phase 0):
  - GPU detection already implemented
  - Local GPU module uses shared detector
  
- [ ] Use `shared/models/memory_manager.py` (built in Phase 0):
  - Memory management already implemented
  - **Confirmed**: Keep models loaded for performance
  - Local GPU module integrates with shared memory manager

#### 1.2 LLM Translation Module
- [ ] Implement `local_gpu_translation/llm_translation/candidate_generator.py`:
  - Load translategemma-12b-it locally (uses shared model_manager)
  - Generate N-best candidates (default: 3-5)
  - Support term injection into prompts
  - Handle quantization (GGUF) for GPU memory efficiency
  - **Keep model loaded** for performance (confirmed requirement)
  
- [ ] Implement `local_gpu_translation/llm_translation/term_extractor.py`:
  - Extract relevant terms from TBX/CSV termbases
  - Match terms to source segment content
  - Format terms for prompt injection
  - Select top-K terms (configurable, default: 8)

- [ ] Implement `local_gpu_translation/llm_translation/prompt_builder.py`:
  - **NEW**: Build prompts from externalized templates
  - Uses `shared/config/prompt_manager.py` to load templates
  - Support two versions: with terms and without terms
  - Format terms for injection into prompt templates
  - Handle tag preservation instructions
  - Template format: INI file with sections for different prompt types

- [ ] Implement `local_gpu_translation/llm_translation/translator.py`:
  - Main translation orchestrator
  - Coordinate candidate generation
  - Handle term injection workflow via prompt_builder
  - Uses shared model_manager for model loading (keeps model loaded)

#### 1.3 TMX Matching
- [ ] Implement `local_gpu_translation/integration/tmx_matcher.py`:
  - Exact source text matching
  - Fuzzy matching (rapidfuzz) with configurable threshold
  - **Exact match** (100% similarity) → Use TMX translation directly, skip LLM
  - **High fuzzy match** (≥threshold, e.g., 75-99%) → Pass to LLM for repair/improvement:
    - LLM receives source segment + fuzzy match translation
    - Uses fuzzy repair prompt template (with/without terms based on termbase availability)
    - LLM task: Repair/improve the translation using externalized prompt templates
    - Generate 3-5 repaired candidate variations
    - Prompt includes: tag preservation, terminology correction, fluency improvement
  - **Low fuzzy match** (<threshold) → Generate new LLM translation
  - **No match** → Generate new LLM translation

#### 1.4 Workflow Orchestration
- [ ] Implement `local_gpu_translation/integration/workflow_manager.py`:
  - Detect available assets (XLIFF, TMX, TBX)
  - Route to appropriate workflow:
    - XLIFF only → minimal processing, translate missing segments
    - XLIFF + TMX → TMX match first (exact skip, fuzzy repair), then LLM for remaining
    - XLIFF + TMX + TBX → Full workflow with term injection
  - Coordinate between modules
  - **Batch processing**: Process in chunks of 100 segments, save partial results every 50 segments
  - Use shared TQE engine for scoring

---

### Phase 2: Quality Estimation Integration (Week 5)

#### 2.1 TQE Integration with Local GPU Module
- [ ] Use `shared/tqe/tqe.py` (built in Phase 0):
  - TQE engine already built as reusable module
  - Integrate with local GPU candidate generator
  - Batch scoring for efficiency
  - Handle segment-level failures gracefully
  
- [ ] Use `shared/tqe/uqlm_integration.py` (built in Phase 0):
  - UQLM integration already implemented in shared module
  - Local GPU module uses shared UQLM integration
  - Don't bundle UQLM, fetch on-demand (already handled)

#### 2.2 Terminology Validation
- [ ] Enhance existing `tqe/terminology.py`:
  - Validate term usage in LLM candidates
  - Calculate term-match scores
  - Support strict/soft enforcement policies
  - Flag missing approved terms

#### 2.3 Scoring & Selection
- [ ] Implement scoring aggregation:
  - Weighted combination of accuracy, fluency, tone, term-match
  - Default weights: 0.6, 0.25, 0.15, 0.1 (configurable per profile)
  - Decision buckets (configurable per profile with global fallback):
    - Accept auto: ≥threshold_accept_auto (default 85), no hallucination, terms satisfied
    - Accept with review: threshold_accept_with_review to threshold_accept_auto (default 70-84)
    - Needs human revision: <threshold_accept_with_review (default <70) or hallucination or term failure
  - Profile-specific thresholds take precedence, fall back to global defaults if not specified

---

### Phase 3: XLIFF Integration & Metadata (Weeks 6-7)

#### 3.1 XLIFF Processing
- [ ] Implement `io/xliff_processor.py`:
  - Parse XLIFF 1.2 and 2.0/2.1/2.2
  - Preserve all existing metadata
  - Handle both `<trans-unit>` (1.2) and `<unit>` (2.x)
  - Preserve inline tags and formatting

- [ ] Implement `io/metadata_writer.py`:
  - Write TQE metadata as `prop-group` props
  - Include standard match rate prop for TMS compatibility
  - Add comment metadata for flagged segments
  - Format: `tqe:*` props for quality metrics
  - Standard prop for match rate (TMS-compatible format)

#### 3.2 Metadata Schema
- [ ] Define metadata structure:
  ```
  tqe:translation_origin - "TMX:exact" | "TMX:fuzzy" | "LLM:translategemma-12b-it"
  tqe:accuracy - 0-100
  tqe:fluency - 0-100
  tqe:tone - 0-100
  tqe:term_match - 0-100
  tqe:weighted_score - 0-100
  tqe:match_rate - 0-100 (TMS-compatible equivalent match rate)
  tqe:decision - "accept_auto" | "accept_with_review" | "needs_human_revision"
  tqe:uqlm_hallucination - boolean
  tqe:models_used - JSON string
  tqe:timestamp - ISO timestamp
  ```
  
- [ ] Add comment metadata for low-quality segments:
  - Format: `<note>` element with quality warnings
  - Include specific issues (low_accuracy, missing_terms, hallucination)
  - Visible in Trados Studio and TMS platforms

---

### Phase 4: Configuration & Profiles (Week 8)

#### 4.1 Profile Management Integration
- [ ] Use `shared/config/profile_manager.py` (built in Phase 0):
  - Profile management already implemented in shared module
  - **User-specific profiles only**: Users see only their own profiles + global
  - Storage: `{install_dir}/config/profiles/{user_id}/` (with auth) or `{install_dir}/config/profiles/global/` (without auth)
  - Global fallback for missing profile settings
  - Local GPU module integrates with shared profile manager
  - Profile switching in UI

- [ ] Define configuration schema:
  ```json
  {
    "profile_name": "ClientA",
    "llm_model": "translategemma-12b-it",
    "num_candidates": 5,
    "term_base_files": ["path/to/terms.csv"],
    "tqe_weights": {
      "accuracy": 0.6,
      "fluency": 0.25,
      "tone": 0.15,
      "term_match": 0.1
    },
    "thresholds": {
      "accept_auto": 85,
      "accept_with_review": 70,
      "needs_human_revision": 70,
      "fuzzy_tmx_threshold": 0.8,
      "term_penalty": 15
    },
    "enforcement_policy": "soft",  // or "strict"
    "comet_models": {
      "ref": "path/to/comet-ref.pt",
      "qe": "path/to/comet-qe.pt"
    },
    "batch_size": null,  // null = auto-tune, else override value
    "language_pairs": ["en-fr", "en-de"]  // optional per-language-pair configs
  }
  ```

#### 4.2 Default Settings & Global Fallback
- [ ] Create global default configuration:
  ```json
  {
    "thresholds": {
      "accept_auto": 85,
      "accept_with_review": 70,
      "needs_human_revision": 70
    },
    "tqe_weights": {
      "accuracy": 0.6,
      "fluency": 0.25,
      "tone": 0.15,
      "term_match": 0.1
    },
    "fuzzy_tmx_threshold": 0.8,
    "batch_size": "auto"
  }
  ```
- [ ] Implement fallback logic:
  - If profile doesn't specify threshold → use global default
  - If no profile active → use global defaults
  - Profile-specific overrides take precedence when available
- [ ] Provide example profiles for common scenarios
- [ ] Documentation for profile creation

---

### Phase 5: API Integration (Weeks 9-10)

#### 5.1 Flask Endpoints
- [ ] Implement `api/endpoints.py`:
  - `/api/llm_translate` - Main translation + TQE endpoint
    - Accept: XLIFF file, optional TMX, optional TBX
    - Return: Processed XLIFF with metadata
  - `/api/llm_translate_status/<job_id>` - Progress tracking
  - `/api/model_status` - Check model availability
  - `/api/download_model` - Trigger model download
  - `/api/config_profiles` - CRUD for configuration profiles

#### 5.2 Progress Tracking
- [ ] Implement progress tracking using existing pattern:
  - **Reuse existing pattern** with new job types
  - New job types added when GPU module installed (update/replace base .tsx file)
  - **SSE for real-time updates** (if supported by existing infrastructure)
  - **Update frequency**: Every 100 segments or 15 seconds (whichever comes first)
  - **Include**: progress %, current phase (matching, translation, scoring), ETA, memory usage
  - Job queue management
  - Chunked processing with intermediate saves (100 segments, save every 50)
  - Cancel capability

#### 5.3 Error Handling
- [ ] Implement `api/error_handler.py`:
  - Segment-level error logging
  - Systematic failure detection (fail fast)
  - Partial result saving
  - User-friendly error messages
  - Error reporting in UI

---

### Phase 6: UI Integration (Weeks 11-12)

#### 6.0 Pre-Implementation UI Review ⚠️ CRITICAL
- [ ] **Review existing UI components** before implementation:
  - Study `dist/New_UI/components/tmx-workspace.tsx` for workspace pattern
  - Study `dist/New_UI/components/operations-panel.tsx` for operations UI pattern
  - Understand existing `Operation` type and how operations are registered
  - Review `OPERATIONS` array structure and operation categorization
  - Understand file upload/processing workflow patterns
  - Review progress tracking implementation (SSE/polling)
  - Identify integration points with existing auth/user management (if available)
- [ ] **Design UI integration approach**:
  - Add new operations to existing `OPERATIONS` array
  - Integrate with existing operations panel/tabs structure
  - Follow existing file upload and workspace patterns
  - Reuse existing progress tracking mechanisms
  - Ensure consistency with existing UI components and styling

#### 6.1 Translation Operations Integration
- [ ] Add translation operations to `OPERATIONS` array in `tmx-workspace.tsx`:
  - `llm_translate`: "Translate with Local LLM"
  - `llm_translate_tqe`: "Translate & Quality Estimation"
  - Operations should follow existing `Operation` type structure
- [ ] Enhance `operations-panel.tsx` to support translation operations:
  - Add new tab/category for "Translation & QA" operations
  - Support multi-file upload (XLIFF + optional TMX + optional TBX)
  - Configuration profile selector (if user management available)
  - Integration with existing queue system
- [ ] Enhance `tmx-workspace.tsx` to handle translation operations:
  - Multi-file handling for XLIFF + TMX + TBX
  - Progress tracking for long-running translation jobs
  - Results display with quality metrics summary
  - Integration with existing processing history

#### 6.2 Model Manager Integration
- [ ] Create `ui/local_gpu/model_manager_panel.tsx` following existing panel patterns:
  - Use existing Card/Button/Tabs components
  - Model status display (installed/not installed) - uses shared model_manager
  - Download progress indicators
  - Disk space usage visualization
  - Model version information
  - Delete functionality with confirmation
  - GPU detection and requirements display (uses shared gpu_detector)
- [ ] Add model manager access point:
  - Add to settings/menu (if available)
  - Or create separate route/page for model management

#### 6.3 Configuration Profile Management
- [ ] Create `ui/local_gpu/config_profile_editor.tsx`:
  - Follow existing form patterns
  - Profile CRUD operations (uses shared profile_manager)
  - Form validation
  - Profile switching dropdown
  - Settings categories/tabs for organization
  - **User-specific profiles only**: Users see only their own profiles + global
  - Works without auth initially, integrates when available

#### 6.4 Prompt Template Editor
- [ ] Create `ui/local_gpu/prompt_editor.tsx`:
  - **NEW**: UI for editing externalized prompt templates
  - Text editor interface for editing prompts
  - Uses shared prompt_manager
  - Load/save prompt templates
  - Validate prompt syntax
  - Support for template variables ({source_text}, {term_list}, etc.)

#### 6.4 Quality Metrics Display
- [ ] Enhance existing workspace to show quality metrics:
  - Add quality score indicators to file list/status
  - Show summary metrics after processing
  - Flag files with low-quality segments
- [ ] Create quality details view (if needed):
  - Segment-level quality metrics
  - Candidate ranking visualization
  - Metadata display
  - Integration with existing stats dialog pattern (`xliff-stats-dialog.tsx`)

---

### Phase 7: Error Handling & Logging (Week 13)

#### 7.1 Error Recovery
- [ ] Implement `utils/error_recovery.py`:
  - Retry logic for transient errors
  - GPU OOM handling (reduce batch size, retry)
  - Model load failure handling
  - Segment-level error isolation

#### 7.2 Logging
- [ ] Implement `utils/logging.py`:
  - Align with TMXmatic logging format
  - Segment-level logging
  - Error categorization (fatal vs non-fatal)
  - Log rotation and management

#### 7.3 Partial Results
- [ ] Implement partial result saving:
  - Save completed segments periodically
  - Resume capability (future enhancement)
  - Clear indication of partial results in output

---

### Phase 8: Installer & Packaging (Week 14)

#### 8.1 Installer
- [ ] Implement `installer/installer.py`:
  - GPU detection
  - TMXmatic version compatibility check
  - System requirements verification
  - Dependency installation
  - Module installation to TMXmatic

#### 8.2 Version Checking
- [ ] Implement `installer/version_checker.py`:
  - Check TMXmatic version
  - Verify compatibility
  - Warn if incompatible

#### 8.3 Documentation
- [ ] Create installation guide
- [ ] Usage documentation
- [ ] API reference
- [ ] Troubleshooting guide

---

## Technical Specifications

### LLM Model Handling
- **Model**: google/translategemma-12b-it
- **Format**: Quantized GGUF for GPU memory efficiency
- **Loading**: On-demand when translation invoked
- **Unloading**: After translation completes (optional, configurable)

### GPU Memory Management
- **8GB RTX**: Use 4-bit quantization, small batch sizes (1-2)
- **12GB RTX**: Use 8-bit quantization, medium batch sizes (4-8)
- **16GB RTX**: Use 8-bit or 16-bit, larger batch sizes (8-16)
- **Auto-adjust**: Monitor memory usage and adjust dynamically

### Batching Strategy
- **Chunked Processing**: Process XLIFF in chunks of 100 segments
- **Progress Updates**: Update every 10 segments
- **Checkpointing**: Save partial results every 50 segments
- **Interrupt Handling**: Graceful shutdown with partial results

### UQLM Integration
- **Source**: Pull from cvs-health/uqlm GitHub repo
- **Installation**: On-demand installation during module setup
- **Usage**: Run on all LLM-generated candidates
- **Output**: Hallucination flag per segment

### Term Extraction Logic
- **Source Matching**: Find terms in termbase matching source segment
- **Top-K Selection**: Select top 8 most relevant terms (configurable)
- **Prompt Format**: Structured term table in prompt
- **Validation**: Check term usage in all candidates post-generation

### TMX Matching Priority
1. **Exact Match** (similarity = 100%): Source text exactly matches TMX entry → Use TMX target directly, skip LLM
2. **High Fuzzy Match** (similarity ≥ threshold, e.g., 75-99%): 
   - Pass source segment + fuzzy TMX translation to LLM
   - **LLM Task**: Repair and improve the fuzzy match translation
   - LLM can fix errors, improve fluency, align terminology, correct grammar
   - Generate N-best repaired candidates for TQE scoring
3. **Low Fuzzy Match** (similarity < threshold but > 0): Generate new LLM translation, score against fuzzy match as reference
4. **No Match** (similarity = 0): Generate new LLM translation from scratch

### Metadata Format for TMS Compatibility

Based on OASIS XLIFF specifications and TMS tool practices, we will use standard XLIFF match rate formats:

#### XLIFF 1.2 Format
- **`<alt-trans>` element**: Include alternate translations with `match-quality` attribute (percentage string like "95%")
- **`state-qualifier` attribute**: On `<target>` element to indicate match type:
  - `exact-match` for 100% matches
  - `fuzzy-match` for 75-99.99% matches
  - `leveraged-tm` for TM matches
- **`extype` attribute**: On `<alt-trans>` to specify match source (e.g., "tm", "mt", "llm")
- **Example**:
  ```xml
  <trans-unit id="tu1">
    <source>Text to translate</source>
    <target state-qualifier="fuzzy-match">Translated text</target>
    <alt-trans match-quality="87%" extype="tm" origin="legacy TM">
      <target>Alternative translation</target>
    </alt-trans>
  </trans-unit>
  ```

#### XLIFF 2.0/2.1/2.2 Format (Translation Candidates Module)
- **Namespace**: `urn:oasis:names:tc:xliff:matches:2.0` (prefix: `mtc`)
- **`<mtc:matches>` element**: Contains one or more `<mtc:match>` elements
- **Match attributes**:
  - `similarity` (0.0-100.0): How similar the source text is to the match source
  - `matchQuality` (0.0-100.0): Quality of the translation candidate (from TQE scoring)
  - `matchSuitability` (0.0-100.0): Combined metric for ranking/selection
  - `type`/`origin`: Source type ("tm", "mt", "tb", "llm", etc.)
- **Example**:
  ```xml
  <unit id="u1">
    <mtc:matches>
      <mtc:match id="m1" similarity="100.0" matchQuality="95.0" matchSuitability="97.5" type="tm" origin="legacy TM">
        <source>Text to translate</source>
        <target>Translated text</target>
      </mtc:match>
    </mtc:matches>
    <segment>
      <source>Text to translate</source>
      <target>Translated text</target>
    </segment>
  </unit>
  ```

#### Match Rate Mapping
- **TMX exact match**: 100% → `similarity=100.0`, `matchSuitability=100.0`, `type="tm"`, `state-qualifier="exact-match"`
- **TMX fuzzy match**: 75-99% → `similarity=75.0-99.0`, `matchSuitability=calculated`, `type="tm"`, `state-qualifier="fuzzy-match"`
- **LLM high quality** (weighted_score ≥ 85): 75-85% → `matchQuality=85-100`, `matchSuitability=calculated`, `type="llm"`
- **LLM medium quality** (70-84): 60-74% → `matchQuality=70-84`, `matchSuitability=calculated`, `type="llm"`
- **LLM low quality** (< 70): 0-59% → `matchQuality=0-69`, `matchSuitability=calculated`, `type="llm"`, flag in notes

#### Match Suitability Calculation
- Formula: `matchSuitability = w1 * similarity + w2 * matchQuality` (normalized to 0-100)
- Default weights: 0.5 for similarity, 0.5 for matchQuality (user-configurable per profile)
- For TM matches: Use similarity as primary, matchQuality from TM metadata if available
- For LLM matches: Use matchQuality from TQE as primary, similarity = 0 (new translation)

#### Quality Warnings (Standard `<note>` Elements)
- Format: `<note category="quality">Quality warning: Low accuracy score (45/100)</note>`
- Place in: `<trans-unit>` (XLIFF 1.2) or `<unit>` (XLIFF 2.0)
- Visible in: Trados Studio, Phrase TMS, Crowdin, Trados Enterprise
- **NO custom props**: All metadata uses standard XLIFF elements only

#### Thresholds
- **Exact match**: matchSuitability ≥ 95% and similarity = 100%
- **Fuzzy match**: matchSuitability ≥ 75% and < 95%
- **Low quality / No match**: matchSuitability < 75% (flagged with quality note)
- **XTM/TMS compatibility**: Matches below 75% treated as "no match" by most TMS tools

---

## Resolved Questions & Decisions

### Critical Questions - RESOLVED ✅

1. **UQLM Specifics** ✅
   - **Repo**: https://github.com/cvs-health/uqlm
   - **Installation**: Python package via `pip install uqlm` (pull from repo, don't bundle)
   - **Documentation**: https://cvs-health.github.io/uqlm/latest/index.html
   - **Scorers**: Supports black-box, white-box, LLM-as-judge, and ensemble scorers
   - **Integration**: Use LangChain-compatible interface, works with various LLM backends
   - **GPU/CPU**: Depends on underlying model; supports both

2. **translategemma-12b-it Details** ✅
   - **Model ID**: `google/translategemma-12b-it`
   - **HuggingFace**: https://huggingface.co/google/translategemma-12b-it/tree/main
   - **Quantization**: Support INT8/INT4 for lower VRAM; research GGUF format options
   - **Hardware**: Target RTX 8GB/12GB/16GB GPUs
   - **Licensing**: Check Google's Gemma license terms

3. **Match Rate Prop Standard** ✅ RESOLVED
   - **Decision**: Use standard XLIFF match rate formats per OASIS specifications
   - **XLIFF 1.2**: Use `<alt-trans match-quality="XX%">` and `state-qualifier` on `<target>`
   - **XLIFF 2.0+**: Use Translation Candidates module with `<mtc:matches>` containing `<mtc:match>` elements
   - **Attributes**: `similarity`, `matchQuality`, `matchSuitability`, `type`, `origin`
   - **Namespace**: `urn:oasis:names:tc:xliff:matches:2.0` (prefix: `mtc`)
   - **Target Platforms**: Trados Studio, Phrase TMS, Crowdin, Trados Enterprise (all support these standards)
   - **Thresholds**: <75% treated as "no match", 75-94.99% fuzzy match, ≥95% exact match
   - **Quality warnings**: Use standard `<note category="quality">` elements (NOT custom props)

4. **Configuration Profile Storage** ✅
   - **Location**: `{TMXmatic_install_dir}/config/profiles/`
   - **Format**: JSON/YAML per profile
   - **Future**: Consider user-specific subdirectories if multi-user support needed

5. **Language Pair Handling** ✅
   - **Decision**: Process all language pairs after auto-detection
   - **Implementation**: Detect all source-target pairs in XLIFF, process each separately
   - **Multi-pair Support**: One profile can support multiple language pairs

6. **Term Injection Format** ✅
   - **Format**: Simple list format (unless testing reveals better practices)
   - **Example**: "Use these approved terms: term1→translation1, term2→translation2"
   - **Future**: Refine based on translategemma testing results

7. **Systematic Failure Detection** ✅
   - **Trigger**: Consecutive failures (configurable threshold, default: 5)
   - **Behavior**: After N consecutive failures, fail fast and save partial results
   - **Logging**: Log each failure before triggering fail-fast

8. **Progress Tracking Implementation** ✅
   - **Method**: Polling + Server-Sent Events (SSE)
   - **Primary**: SSE for real-time push updates
   - **Fallback**: Polling if SSE not supported
   - **Update Frequency**: Every 10 segments or 5 seconds (whichever comes first)

### Nice-to-Have Clarifications - RESOLVED ✅

9. **Model Versioning** ✅
   - **Update Process**: Manual from model manager screen
   - **UI**: "Check for Updates" button triggers version check
   - **Behavior**: Show available updates, user initiates download
   - **Versions**: Store model versions, allow downgrade if needed

10. **Batch Size Tuning** ✅
    - **Approach**: Both auto-tune and manual override
    - **Default**: Auto-tune based on GPU memory and segment length
    - **Override**: User-configurable per profile in config settings
    - **Fallback**: If auto-tune fails, prompt user to set manually

11. **Termbase Format Priority** ✅
    - **Initial**: Limit to one termbase (TBX or CSV) per profile
    - **Priority**: If both provided, prompt user to choose
    - **Future**: Support multiple termbases if user feedback indicates need

12. **Quality Threshold Customization** ✅ RESOLVED
    - **Decision**: Per-profile thresholds with global fallback
    - **Implementation**: 
      - Each profile can define custom thresholds (accept_auto, accept_with_review, needs_human_revision)
      - If no profile is active or profile lacks thresholds, fall back to global defaults
      - Global defaults: accept_auto ≥85, accept_with_review 70-84, needs_human_revision <70
    - **Future**: Domain-specific and per-language-pair thresholds can be added as profile options

## Remaining Open Questions

### Research Completed ✅

1. **XLIFF Match Rate Prop Format** ✅ COMPLETED
   - **Standard**: OASIS XLIFF specifications define match rate formats
   - **XLIFF 1.2**: `<alt-trans match-quality="XX%">` and `state-qualifier` attributes
   - **XLIFF 2.0+**: Translation Candidates module with `similarity`, `matchQuality`, `matchSuitability` attributes
   - **Compatibility**: All major TMS platforms (Trados Studio, Phrase TMS, Crowdin, Trados Enterprise) support these standards
   - **Implementation**: Support both formats based on input XLIFF version

2. **translategemma Quantization Options**:
   - Verify availability of pre-quantized versions (GGUF, INT8, INT4)
   - Test quantization approaches for best quality/speed tradeoff
   - **Action**: Test different quantization formats during Phase 1

### Implementation Decisions Pending

3. **Quality Threshold Defaults**:
   - Specific numeric thresholds for accept_auto, accept_with_review, needs_human_revision
   - Whether to use TQE weighted score alone or combination with UQLM confidence
   - **Action**: Determine during Phase 2 testing phase

---

## Success Criteria

### Functional
- ✅ Successfully translate XLIFF segments using local LLM
- ✅ Match TMX entries and skip LLM when match found
- ✅ Inject terminology into LLM prompts
- ✅ Score translations with TQE metrics
- ✅ Write comprehensive metadata to XLIFF
- ✅ Flag low-quality segments for review
- ✅ Handle errors gracefully with partial results

### Performance
- ✅ Process 1000 segments in < 30 minutes on RTX 12GB
- ✅ GPU memory usage < 90% of available
- ✅ Progress updates every 10 seconds
- ✅ Fail fast detection within 5 failed segments

### User Experience
- ✅ Clear error messages in UI
- ✅ Progress indicators for long operations
- ✅ Model management accessible from UI
- ✅ Configuration profiles easy to create/edit
- ✅ Quality metrics visible per segment

### Technical
- ✅ Compatible with TMXmatic existing architecture
- ✅ Logging aligned with TMXmatic standards
- ✅ No breaking changes to existing TMXmatic functionality
- ✅ Installer works on Windows 10/11

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| GPU OOM | Quantized models, dynamic batch sizing, CPU fallback |
| Model download failures | Resume capability, multiple mirror sources |
| UQLM integration issues | Isolated integration, optional dependency |
| Large file processing | Chunked processing, checkpointing |
| Performance issues | Profiling, optimization, user expectations |

### User Experience Risks

| Risk | Mitigation |
|------|------------|
| Complex configuration | Default profiles, wizard for setup |
| Unclear error messages | Detailed logging, user-friendly UI messages |
| Long processing times | Progress indicators, ability to cancel |
| Missing models | Clear installation instructions, auto-download option |

---

## Timeline Summary

- **Week 1**: Shared Infrastructure Foundation (Phase 0) ✅ NEW
- **Weeks 2-4**: Foundation & Core Translation (Phase 1)
- **Week 5**: Quality Estimation Integration (Phase 2)
- **Weeks 6-7**: XLIFF Integration & Metadata (Phase 3)
- **Week 8**: Configuration & Profiles (Phase 4)
- **Weeks 9-10**: API Integration (Phase 5)
- **Weeks 11-12**: UI Integration (Phase 6)
- **Week 13**: Error Handling & Logging (Phase 7)
- **Week 14**: Installer & Packaging (Phase 8)

**Total Estimated Duration**: 14 weeks (~3.5 months)

**Note**: Phase 0 (Shared Infrastructure) benefits both Local GPU Module and future Multi-Agent System. The shared infrastructure investment pays off when building Multi-Agent System later.

---

## Next Steps

1. ✅ **All clarifications received**: 9/9 questions answered (see `CLARIFICATIONS_AND_QUESTIONS.md`)
2. ✅ **Architecture decision made**: Option B (Shared Infrastructure) confirmed
3. ✅ **Implementation plan updated**: All confirmed answers incorporated
4. **Review and approve** this final implementation plan
5. **Set up development environment**:
   - Clone repository: `https://github.com/Ben408/TMXmatic`
   - Checkout branch: `Local_translate_QA`
   - Set up local development environment
6. **Pre-implementation tasks**:
   - Review existing UI components in `dist/New_UI/components/`
   - Understand existing operations pattern and integration points
   - Review Sage Local `Process_Variants/config.ini` for prompt externalization pattern
   - Check auth/user management integration points (if available)
   - Verify dynamic dependency installation system works with new module
7. **Begin Phase 0**: Build shared infrastructure foundation
8. **Establish testing strategy** and test data preparation

## Key Decisions Summary

✅ **Architecture**: Option B - Shared Infrastructure, Separate Modules  
✅ **Profile Management**: User-specific profiles only  
✅ **Prompt System**: Externalized prompts (INI format), two versions (with/without terms)  
✅ **Model Loading**: Keep models loaded for performance  
✅ **Progress Tracking**: Reuse existing pattern, SSE, 100 segments/15s updates  
✅ **Batch Processing**: 100 segment chunks, save every 50 segments  
✅ **Error Recovery**: Log single failures, fail fast after 5 consecutive failures  
✅ **Model Storage**: Shared models available to all users  
✅ **TMX Matching**: Exact skip, fuzzy repair, no match = new translation

## Important Implementation Notes

### Shared Infrastructure (Option B) ✅ CONFIRMED
- **Build shared components first** (Phase 0): Models, GPU, Config, TQE, Prompts
- **Clean interfaces**: Shared modules expose reusable APIs
- **No tight coupling**: Local GPU and Multi-Agent remain independent
- **Code reuse**: Maximize shared code, minimize duplication
- **Future-proof**: Multi-Agent System can use shared infrastructure without modification
- **Benefits**: 
  - Local GPU module benefits immediately from shared infrastructure
  - Multi-Agent System will benefit from GPU module development
  - Can challenge assumptions about multi-agent system after GPU module complete
  - Implementation details of multi-agent can change without affecting goals

### UI Integration Strategy
- **Follow existing patterns**: Study `tmx-workspace.tsx` and `operations-panel.tsx` before implementing
- **Extend, don't replace**: Add new operations to existing `OPERATIONS` array
- **Consistency**: Use existing UI components, styling, and patterns
- **Progressive enhancement**: Module should work even if auth/user management not yet available

### TMX Matching Clarification
- **Exact matches** (100% similarity): Use TMX translation directly, skip LLM
- **High fuzzy matches** (≥threshold): LLM repairs/improves the fuzzy match translation
- **Low/no matches**: LLM generates new translation

### Configuration System
- **Per-profile thresholds** with **global fallback**
- **User-specific profiles only**: Users see only their own profiles + global
- Profiles stored in `{TMXmatic_install_dir}/config/profiles/{user_id}/` (with auth) or `{install_dir}/config/profiles/global/` (without auth)
- Global defaults used when profile doesn't specify or no profile active
- Future: Support per-language-pair thresholds within profiles

### Prompt Externalization System
- **Externalized prompts**: INI format following Sage Local pattern
- **Location**: `{install_dir}/config/prompts/prompt_templates.ini`
- **Two versions per prompt type**: With terms and without terms
- **Template sections**:
  - `[fuzzy_repair_with_terms]` - Fuzzy match repair with approved terms
  - `[fuzzy_repair_without_terms]` - Fuzzy match repair without terms
  - `[new_translation_with_terms]` - New translation with approved terms
  - `[new_translation_without_terms]` - New translation without terms
- **Tag preservation**: Explicit instructions to preserve all tags in correct order
- **User-editable**: UI allows users to edit prompt templates
- **Default templates**: Included with module installation
- **Reference**: Sage Local `Process_Variants/config.ini` for pattern examples

### Relationship with Multi-Agent System (Option B Architecture)
- **Option B Selected**: Shared Infrastructure, Separate Modules
- **Shared Components**: Model management, GPU management, TQE scoring, configuration management, prompt management
- **Different approaches**: 
  - Local GPU module: Uses **local GPU-based LLM** (translategemma-12b-it)
  - Multi-agent system: Uses **serverless LLM endpoints** (RunPod/HF) but also requires GPU for some agents
- **Shared Infrastructure Benefits**:
  - Both systems use same model/GPU management
  - Both systems use same TQE scoring engine
  - Both systems use same configuration/profile system
  - Multi-agent system can be built faster using shared infrastructure
- **Complementary systems**: Both can coexist, serving different use cases:
  - Local GPU module: For users with RTX GPUs who want privacy/offline processing
  - Multi-agent system: For cloud-based processing with advanced orchestration, can also use local GPU when available
- **Development Strategy**: 
  - Build shared infrastructure now (Phase 0)
  - Build Local GPU module using shared infrastructure
  - Multi-agent system can challenge assumptions and benefit from GPU module development
  - Implementation details of multi-agent can change without affecting goals
- **No conflicts**: Different deployment models, different user needs, shared foundation

## All Questions Answered ✅

All clarifications have been received and incorporated. See `CLARIFICATIONS_AND_QUESTIONS.md` for complete Q&A record.

### Decisions Summary

1. **Auth/User Management Integration**:
   - When auth/user management is available, how should profile management integrate?
   - Should profiles be user-specific or shared across organization?
   - How to handle user context in API calls?

2. **LLM Prompt Engineering for Fuzzy Match Repair**:
   - What specific prompt format should be used for "repair fuzzy match" task?
   - Should we use a template like: "The following translation is a fuzzy match (XX% similarity) for the source. Please repair and improve it to better match the source while maintaining meaning: [source] [fuzzy translation]"
   - Or more detailed instructions about what types of repairs to focus on?

3. **Fuzzy Match Repair vs New Translation**:
   - For high fuzzy matches, should we generate multiple candidates that include:
     - Repaired versions of the fuzzy match
     - New translations (for comparison)
   - Or only repaired versions of the fuzzy match?

4. **Dynamic Dependencies Integration**:
   - How should this module's dependencies (torch, transformers, etc.) integrate with the existing dynamic dependency system?
   - Should model downloads also use the dynamic dependency installation pattern?

### Medium Priority

5. **Okapi Integration Relationship**:
   - Should this module be aware of Okapi processing that might happen before/after?
   - Any file format considerations when Okapi processes files first?

6. **Multi-Agent System Future Integration**:
   - Should we design TQE scoring to be reusable by multi-agent system?
   - Any shared interfaces or APIs we should maintain?

7. **Workspace File Management**:
   - How should processed files with quality metadata be handled in the existing workspace?
   - Should quality scores be visible in file list or only in details?

### Low Priority

8. **Model Caching Strategy**:
   - Should model downloads be shared across users in multi-user scenarios?
   - Or per-user model storage?

9. **Progress Tracking Implementation Details**:
   - Should we use the existing progress tracking pattern from `tmx-workspace.tsx`?
   - Or create new SSE endpoints specifically for translation jobs?

---

## Appendix: Key Dependencies

### Python Packages
- torch (with CUDA support)
- transformers (HuggingFace)
- sentence-transformers
- bert-score
- lxml (XLIFF parsing)
- rapidfuzz (fuzzy matching)
- huggingface-hub (model downloads)
- comet (Unbabel COMET)
- flask (API endpoints)

### External Tools
- CUDA toolkit (for GPU support)
- UQLM (from cvs-health/uqlm GitHub repo)

### Optional
- llama.cpp or similar (for GGUF quantized models)
- scikit-learn (for calibration, if needed)
