# LLM Quality Module for TMXmatic

A GPU-accelerated translation and quality estimation module for TMXmatic, enabling local translation using RTX 8GB, 12GB, or 16GB GPUs.

## Features

- **Local GPU Translation**: Uses `translategemma-12b-it` for on-device translation
- **Translation Memory Integration**: Exact and fuzzy matching with TMX files
- **Terminology Support**: TBX/CSV termbase integration with term injection
- **Quality Estimation**: Multi-metric scoring (accuracy, fluency, tone, hallucination detection)
- **XLIFF Support**: Full XLIFF 1.2 and 2.0+ support with metadata preservation
- **TMS Compatibility**: Standard match rate properties for Trados Studio, Phrase TMS, etc.
- **REST API**: Flask endpoints for integration with TMXmatic UI
- **CLI Interface**: Command-line tool for batch processing

## Requirements

- Python 3.11+
- CUDA-capable GPU (8GB+ VRAM recommended for translategemma-12b-it)
- Windows 10/11 (primary platform)
- ~25GB disk space for models (translategemma-12b-it: 24GB, SBERT: 0.4GB, COMET: optional)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd "F:\LLM Quality Module for TMXmatic"
```

2. Set up virtual environment:
```bash
setup_venv.bat
```

3. Activate virtual environment:
```bash
.venv\Scripts\Activate.ps1
```

4. Verify models (optional - models will be downloaded on first use):
```bash
python tools/verify_models.py
```

## Model Management

### Required Models
- **translategemma-12b-it** (google/translategemma-12b-it): 24GB - Main translation model
- **SBERT Multilingual** (sentence-transformers/paraphrase-multilingual-mpnet-base-v2): 0.4GB - For similarity scoring

### Optional Models
- **COMET Reference** (Unbabel/wmt22-comet-da): 0.5GB - Reference-based quality estimation
- **COMET-QE** (Unbabel/wmt22-cometkiwi-da): 0.5GB - Quality estimation without reference

Models are automatically downloaded from HuggingFace on first use, or can be downloaded manually via the API or model manager.

## Usage

### Command Line

```bash
python -m local_gpu_translation.main \
    --xliff input.xlf \
    --output output.xlf \
    --tmx memory.tmx \
    --tbx terms.tbx \
    --src-lang en \
    --tgt-lang fr \
    --profile ClientA
```

### API Endpoints

The module provides Flask API endpoints:

- `GET /gpu/status` - Get GPU status and capabilities
- `GET /models/list` - List available models
- `POST /models/download` - Download a model
- `POST /translate` - Translate XLIFF file
- `GET /translate/download` - Download translated file

## Architecture

### Phase 0: Shared Infrastructure
- GPU detection and management
- Model downloading and caching
- Memory management
- Configuration profiles
- Prompt templates
- TQE engine

### Phase 1: Core Translation
- LLM translation module
- TMX matching (exact/fuzzy)
- Term extraction and injection
- Workflow orchestration

### Phase 2: Quality Estimation
- Multi-metric scoring
- Term validation
- Score aggregation
- Decision making

### Phase 3: XLIFF Integration
- XLIFF parsing and writing
- Metadata preservation
- Match rate calculation
- Quality warnings

## Testing

### Test Results
- **Total Tests**: 202
- **All Passing**: ✅ 202/202
- **Coverage**: 80-97% for tested components
- **Execution Time**: ~12 seconds

### Running Tests

Run all tests:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=shared --cov=local_gpu_translation --cov-report=html
```

Run specific test suites:
```bash
# Phase 0: Shared Infrastructure
pytest tests/unit/shared/ -v

# Phase 1: Core Translation
pytest tests/unit/local_gpu/ -v

# Integration tests
pytest tests/integration/ -v
```

### Test Documentation
- **Comprehensive Test Report**: See `COMPREHENSIVE_TEST_REPORT.md`
- **Coverage Analysis**: See `TEST_COVERAGE_ANALYSIS.md`
- **Test Results**: See `TEST_RESULTS.md`

## Project Structure

```
F:\LLM Quality Module for TMXmatic/
├── shared/                 # Shared infrastructure
│   ├── gpu/              # GPU detection
│   ├── models/             # Model management
│   ├── config/             # Configuration
│   ├── tqe/                # Quality estimation
│   └── utils/               # Utilities
├── local_gpu_translation/   # Main module
│   ├── llm_translation/     # LLM translation
│   ├── integration/         # Workflow orchestration
│   ├── io/                  # XLIFF processing
│   ├── quality/             # Quality validation
│   └── api/                 # Flask endpoints
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
└── Models/                  # Downloaded models
```

## Configuration

Configuration profiles are stored in `config/profiles/` and support:
- Model selection
- TQE weights and thresholds
- Term enforcement policies (strict/soft)
- Batch processing settings
- Language pair specific settings

### Profile Structure
```json
{
  "profile_name": "ClientA",
  "llm_model": "translategemma-12b-it",
  "num_candidates": 5,
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
  }
}
```

## Workflow

1. **TMX Matching**: Exact matches (100%) use TMX directly, fuzzy matches (≥75%) are repaired by LLM
2. **Term Injection**: Relevant terms from TBX/CSV are injected into prompts
3. **Translation**: LLM generates N-best candidates
4. **Quality Estimation**: Candidates scored using accuracy, fluency, tone, and hallucination detection
5. **Selection**: Best candidate selected based on weighted scores
6. **Metadata**: Match rates and quality scores written to XLIFF for TMS compatibility

## API Integration

The module provides Flask Blueprint (`local_gpu_bp`) that can be registered with the main TMXmatic Flask app:

```python
from local_gpu_translation.api.endpoints import local_gpu_bp
app.register_blueprint(local_gpu_bp)
```

## Status

✅ **Core Implementation Complete**
- All 202 tests passing
- Comprehensive test coverage
- Full documentation
- Ready for UI integration

⚠️ **Models Required**
- Models must be downloaded before use
- Use `tools/verify_models.py` to check model status
- Models download automatically on first use

## Documentation

### Main Documentation
- **Installation & Integration**: `docs/INSTALLATION.md` - Complete installation guide
- **Testing**: `docs/TESTING.md` - Test strategy, results, and coverage
- **UI Integration**: `docs/UI_INTEGRATION.md` - UI components and integration
- **Cognee Review**: `docs/COGNEE_REVIEW.md` - Review for multi-agent system

### Module-Specific
- **TQE Module**: `tqe/README.md` - Translation Quality Estimation module

### Archived Documentation
- Original documentation files preserved in `docs/archive/` for reference

## Branch Information

- **Branch**: `Local_translate_QA`
- **Repository**: https://github.com/Ben408/TMXmatic
- **Status**: Ready for check-in

## License

[Your License Here]

## Contributing

[Contributing Guidelines]
