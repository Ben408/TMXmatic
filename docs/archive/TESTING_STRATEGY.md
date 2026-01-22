# Testing Strategy for LLM Quality Module

## Overview

This document outlines the comprehensive testing strategy for the LLM Quality Module for TMXmatic. Testing will be performed at multiple levels: unit tests, integration tests, and system tests.

## Testing Philosophy

1. **Test-Driven Development**: Write tests alongside implementation
2. **Comprehensive Coverage**: Aim for >80% code coverage
3. **Isolated Tests**: Each test should be independent and repeatable
4. **Real Data**: Use realistic test files (XLIFF, TMX, TBX)
5. **Mock External Dependencies**: Mock GPU, model downloads, and external APIs
6. **Documentation**: All tests must be documented with purpose and expected behavior

## Test Structure

```
tests/
├── unit/                      # Unit tests for individual components
│   ├── shared/               # Tests for shared infrastructure
│   │   ├── test_models/
│   │   ├── test_config/
│   │   ├── test_tqe/
│   │   └── test_utils/
│   ├── local_gpu/            # Tests for local GPU module
│   │   ├── test_llm_translation/
│   │   ├── test_integration/
│   │   └── test_io/
│   └── test_api/             # API endpoint tests
├── integration/              # Integration tests
│   ├── test_workflows/       # End-to-end workflow tests
│   ├── test_file_processing/ # File I/O integration tests
│   └── test_model_management/ # Model download/loading tests
├── fixtures/                 # Test data files
│   ├── xliff/               # Sample XLIFF files
│   ├── tmx/                 # Sample TMX files
│   ├── tbx/                 # Sample TBX files
│   └── config/              # Test configuration files
└── conftest.py              # Pytest configuration and fixtures
```

## Testing Framework

- **Framework**: pytest
- **Coverage**: pytest-cov
- **Mocking**: unittest.mock, pytest-mock
- **Fixtures**: pytest fixtures for common test data

## Test Categories by Phase

### Phase 0: Shared Infrastructure

#### Shared Model Management
- [ ] `test_gpu_detector.py`: GPU detection, memory detection, graceful fallback
- [ ] `test_model_manager.py`: Model download, caching, versioning, cleanup
- [ ] `test_memory_manager.py`: Memory monitoring, batch size adjustment, OOM handling

#### Shared Configuration
- [ ] `test_profile_manager.py`: Profile CRUD, user-specific profiles, global fallback
- [ ] `test_prompt_manager.py`: Prompt loading, template validation, variable substitution

#### Shared TQE
- [ ] `test_tqe_scoring.py`: BERTScore, SBERT, COMET scoring
- [ ] `test_terminology_validation.py`: Term matching, term presence checking
- [ ] `test_uqlm_integration.py`: Hallucination detection integration

#### Shared Utilities
- [ ] `test_logging.py`: Logging utilities, log file rotation
- [ ] `test_error_recovery.py`: Retry logic, error classification

### Phase 1: Foundation & Core Translation

#### LLM Translation
- [ ] `test_candidate_generator.py`: N-best generation, term injection, quantization
- [ ] `test_term_extractor.py`: Term extraction from TBX/TMX, term matching
- [ ] `test_prompt_builder.py`: Prompt template building, variable substitution
- [ ] `test_translator.py`: Translation orchestration, model lifecycle

#### TMX Matching
- [ ] `test_tmx_matcher.py`: Exact matching, fuzzy matching, threshold handling
- [ ] `test_fuzzy_repair.py`: Fuzzy match repair prompts, candidate generation

#### Workflow Orchestration
- [ ] `test_workflow_manager.py`: Asset detection, workflow routing, batch processing
- [ ] `test_asset_coordinator.py`: XLIFF/TMX/TBX coordination

### Phase 2: Quality Estimation Integration

- [ ] `test_tqe_integration.py`: TQE scoring integration with translation
- [ ] `test_quality_aggregation.py`: Score aggregation, match rate calculation
- [ ] `test_terminology_qa.py`: Terminology validation in translations

### Phase 3: XLIFF Integration & Metadata

- [ ] `test_xliff_processor.py`: XLIFF parsing, metadata preservation
- [ ] `test_metadata_writer.py`: Match rate writing, quality metadata, standard formats
- [ ] `test_tmx_parser.py`: Enhanced TMX parsing for matching
- [ ] `test_tbx_parser.py`: TBX parsing for terminology

### Phase 4: Configuration & Profiles

- [ ] `test_profile_integration.py`: Profile integration with translation workflow
- [ ] `test_prompt_editing.py`: Prompt template editing and validation

### Phase 5: API Integration

- [ ] `test_endpoints.py`: All Flask endpoints, request/response validation
- [ ] `test_progress_tracking.py`: Progress updates, job status
- [ ] `test_error_handling.py`: API error responses, error codes

### Phase 6: UI Integration

- [ ] `test_ui_components.py`: React component rendering (if using React Testing Library)
- [ ] `test_ui_integration.py`: UI-backend integration tests

### Phase 7: Error Handling & Logging

- [ ] `test_error_recovery_integration.py`: End-to-end error recovery
- [ ] `test_partial_results.py`: Partial result saving, failure handling

### Phase 8: Installer & Packaging

- [ ] `test_installer.py`: Installer script, dependency checking, GPU detection
- [ ] `test_version_compatibility.py`: Version compatibility checks

## Test Data Requirements

### XLIFF Test Files
- [ ] Simple XLIFF (1.2) with single language pair
- [ ] Complex XLIFF (2.0+) with multiple language pairs
- [ ] XLIFF with existing translations
- [ ] XLIFF with empty targets
- [ ] XLIFF with tags and formatting
- [ ] Large XLIFF (>1000 segments)

### TMX Test Files
- [ ] Simple TMX with exact matches
- [ ] TMX with fuzzy matches
- [ ] TMX with metadata (creation dates, usage counts)
- [ ] Large TMX (>10,000 entries)
- [ ] TMX with multiple language pairs

### TBX Test Files
- [ ] Simple TBX with terminology
- [ ] TBX with multiple languages
- [ ] TBX with term variants
- [ ] TBX with definitions and contexts

## Mocking Strategy

### GPU Mocking
- Mock CUDA availability
- Mock GPU memory (8GB, 12GB, 16GB scenarios)
- Mock GPU OOM errors

### Model Mocking
- Mock model downloads (avoid downloading large models in tests)
- Mock model loading/unloading
- Mock inference calls (return deterministic results)

### External API Mocking
- Mock HuggingFace Hub downloads
- Mock UQLM calls (if external service)

## Test Execution

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/shared/test_models/test_model_manager.py

# Run specific test
pytest tests/unit/shared/test_models/test_model_manager.py::test_download_model

# Run with verbose output
pytest -v

# Run only fast tests (skip slow model tests)
pytest -m "not slow"
```

### Continuous Testing

- Run tests before each commit
- Run full test suite in CI/CD pipeline
- Generate coverage reports

## Test Documentation

Each test file must include:
1. **Purpose**: What component/feature is being tested
2. **Test Cases**: List of all test cases with descriptions
3. **Fixtures**: What test data/fixtures are used
4. **Mocking**: What external dependencies are mocked
5. **Coverage**: What code paths are covered

## Test Results Documentation

For each phase:
1. **Test Results Summary**: Pass/fail counts, coverage percentage
2. **Failure Analysis**: Detailed analysis of any failures
3. **Code Remediation**: How failures were fixed
4. **Coverage Report**: Code coverage metrics

## Performance Testing

- Model loading time
- Translation throughput (segments/second)
- Memory usage under load
- Large file processing (1000+ segments)

## Integration Testing

- End-to-end translation workflow
- Multi-asset workflows (XLIFF + TMX + TBX)
- Error recovery scenarios
- Partial result saving

## Regression Testing

- Re-run all tests after each phase
- Ensure no regressions in previous phases
- Maintain test suite as code evolves

## Test Maintenance

- Update tests when requirements change
- Remove obsolete tests
- Refactor tests for clarity
- Keep test documentation up-to-date

---

## Test Execution Log

### Phase 0: Shared Infrastructure
- Status: Not Started
- Tests Written: 0
- Tests Passing: 0
- Coverage: 0%

### Phase 1: Foundation & Core Translation
- Status: Not Started
- Tests Written: 0
- Tests Passing: 0
- Coverage: 0%

[... Additional phases will be documented as implementation progresses ...]
