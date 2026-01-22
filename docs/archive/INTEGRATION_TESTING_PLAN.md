# Full Integration Testing Plan

**Status**: ⏳ **PENDING** - Requires models and test files  
**Estimated Effort**: 2-3 days

---

## Overview

Full integration testing requires actual models and real-world test files to verify the complete translation workflow end-to-end.

---

## Prerequisites

### 1. Models Required

#### Required Models (Must Have)
- ✅ **translategemma-12b-it** (google/translategemma-12b-it)
  - **Size**: 24GB
  - **Purpose**: Main translation model
  - **Download**: Can be automated (see below)

- ✅ **SBERT Multilingual** (sentence-transformers/paraphrase-multilingual-mpnet-base-v2)
  - **Size**: 0.4GB
  - **Purpose**: Similarity scoring, tone matching
  - **Download**: Can be automated (see below)

#### Optional Models (Nice to Have)
- ⚠️ **COMET Reference** (Unbabel/wmt22-comet-da)
  - **Size**: 0.5GB
  - **Purpose**: Reference-based quality estimation
  - **Download**: Can be automated

- ⚠️ **COMET-QE** (Unbabel/wmt22-cometkiwi-da)
  - **Size**: 0.5GB
  - **Purpose**: Quality estimation without reference
  - **Download**: Can be automated

### 2. Test Files Required

#### User-Provided Test Files
- ✅ **TBX**: `C:\Users\bjcor\Desktop\Sage Local\SDMO Glossary\SDMO_multilingual_merged.tbx`
- ✅ **XLIFF**: `C:\Users\bjcor\Desktop\Sage Local\SW XLIFF\error message.xlf`
- ✅ **TMX**: `C:\Users\bjcor\Desktop\TMXmatic\Test_files` (directory)

---

## Model Download Options

### Option 1: Automated Download (Recommended)

**I can create a script to download models**, but you'll need to:

1. **Run the download script**:
   ```bash
   python tools/download_required_models.py
   ```

2. **Requirements**:
   - Internet connection
   - ~25GB free disk space
   - HuggingFace account (for some models, may need token)
   - Time: 1-3 hours depending on connection

3. **What the script does**:
   - Checks disk space
   - Downloads models to `Models/` directory
   - Verifies downloads
   - Reports status

**Status**: ✅ Script created (`tools/download_required_models.py`)

### Option 2: Manual Download

**You can download models manually**:

1. **translategemma-12b-it**:
   - Visit: https://huggingface.co/google/translategemma-12b-it
   - Download using HuggingFace CLI or web interface
   - Place in `Models/google/translategemma-12b-it/`

2. **SBERT**:
   - Auto-downloads on first use (via transformers library)
   - Or download manually from HuggingFace

3. **COMET models** (optional):
   - Use `tools/download_comet_model.py`
   - Or download from HuggingFace

**Status**: ⏳ Manual process, more time-consuming

### Recommendation

**I recommend Option 1 (Automated)**:
- ✅ Script handles everything
- ✅ Verifies downloads
- ✅ Reports progress
- ✅ Can resume if interrupted

**You just need to run**: `python tools/download_required_models.py`

---

## Full Integration Testing Requirements

### Test 1: End-to-End Translation Workflow

**Purpose**: Test complete workflow with real files

**Requirements**:
- ✅ XLIFF file (user provided)
- ✅ TMX file (user provided)
- ✅ TBX file (user provided)
- ⚠️ translategemma-12b-it model (24GB)
- ⚠️ SBERT model (0.4GB, auto-downloads)

**Test Steps**:
1. Load XLIFF file
2. Load TMX file (if provided)
3. Load TBX file (if provided)
4. Initialize translator with model
5. Process segments:
   - Exact TMX matches
   - Fuzzy TMX matches (LLM repair)
   - New translations
6. Score candidates with TQE
7. Write results to output XLIFF
8. Verify output:
   - Translations present
   - Match rates written
   - Quality scores written
   - Metadata preserved

**Expected Output**:
- Translated XLIFF file
- Quality scores in metadata
- Match rates in standard format
- Statistics report

**Test File**: `tests/integration/test_full_workflow_real_files.py`

---

### Test 2: Model Loading and Inference

**Purpose**: Verify models can be loaded and used

**Requirements**:
- ⚠️ translategemma-12b-it model
- ⚠️ SBERT model

**Test Steps**:
1. Load translategemma model
2. Generate translation candidates
3. Verify candidates are generated
4. Load SBERT model
5. Compute similarity scores
6. Verify scores are reasonable

**Test File**: `tests/integration/test_model_loading.py`

---

### Test 3: Large File Processing

**Purpose**: Test with large XLIFF files (1000+ segments)

**Requirements**:
- Large XLIFF file (or generate one)
- All models loaded

**Test Steps**:
1. Process XLIFF with 1000+ segments
2. Verify batch processing works
3. Verify partial saves work
4. Verify memory management
5. Verify progress tracking

**Test File**: `tests/integration/test_large_files.py`

---

### Test 4: Error Recovery

**Purpose**: Test error handling with real failures

**Requirements**:
- Models loaded
- Test files

**Test Steps**:
1. Simulate GPU OOM
2. Test partial result saving
3. Test retry logic
4. Test error reporting

**Test File**: `tests/integration/test_error_recovery.py`

---

### Test 5: COMET Integration

**Purpose**: Test COMET models if available

**Requirements**:
- ⚠️ COMET Reference model (optional)
- ⚠️ COMET-QE model (optional)

**Test Steps**:
1. Load COMET models
2. Score translations with COMET
3. Verify scores are reasonable
4. Test batch processing

**Test File**: `tests/integration/test_comet_integration.py`

---

## Implementation Plan

### Phase 1: Model Download (Day 1)

**Tasks**:
1. ✅ Create download script (`tools/download_required_models.py`)
2. ⏳ Run download script (user action required)
3. ⏳ Verify models downloaded
4. ⏳ Test model loading

**Estimated Time**: 2-4 hours (mostly download time)

### Phase 2: Integration Test Creation (Day 2)

**Tasks**:
1. Create `tests/integration/test_full_workflow_real_files.py`
2. Create `tests/integration/test_model_loading.py`
3. Create `tests/integration/test_large_files.py`
4. Create `tests/integration/test_error_recovery.py`
5. Create `tests/integration/test_comet_integration.py`

**Estimated Time**: 4-6 hours

### Phase 3: Test Execution and Fixes (Day 3)

**Tasks**:
1. Run all integration tests
2. Fix any bugs discovered
3. Document results
4. Update coverage reports

**Estimated Time**: 4-6 hours

---

## What I Can Do vs. What You Need to Do

### ✅ I Can Do (Automated)
1. **Create download script** - ✅ DONE (`tools/download_required_models.py`)
2. **Create integration test files** - ⏳ Can create now
3. **Test structure and framework** - ✅ Already in place

### ⚠️ You Need to Do (Manual)
1. **Run download script** - Requires:
   - Internet connection
   - ~25GB disk space
   - 1-3 hours (download time)
   - HuggingFace account (may need token for some models)

2. **Provide test files** - Already provided:
   - ✅ TBX: `C:\Users\bjcor\Desktop\Sage Local\SDMO Glossary\SDMO_multilingual_merged.tbx`
   - ✅ XLIFF: `C:\Users\bjcor\Desktop\Sage Local\SW XLIFF\error message.xlf`
   - ✅ TMX: `C:\Users\bjcor\Desktop\TMXmatic\Test_files`

3. **Run integration tests** - After models downloaded

---

## Recommended Approach

### Step 1: Download Models (You)
```bash
cd "F:\LLM Quality Module for TMXmatic"
.venv\Scripts\Activate.ps1
python tools/download_required_models.py
```

**Time**: 1-3 hours (mostly waiting for downloads)

### Step 2: Create Integration Tests (Me)
I can create all integration test files now, ready to run once models are downloaded.

### Step 3: Run Tests (You/Me)
Once models are downloaded, we can run the integration tests.

---

## Alternative: Test with Smaller Models

If downloading 24GB is not feasible right now, we can:

1. **Use smaller test models** for integration tests
2. **Mock model inference** more comprehensively
3. **Test with actual models later** in staging/production

This would allow integration testing without the full model download.

---

## Next Steps

### Immediate (You)
1. **Decide**: Download models now or use smaller models for testing?
2. **If downloading**: Run `python tools/download_required_models.py`
3. **If using smaller models**: Let me know and I'll create alternative tests

### Immediate (Me)
1. **Create integration test files** (ready to run once models available)
2. **Enhance mocking** (if you prefer to test without full models)
3. **Create test file helpers** (to use your provided test files)

---

## Summary

### Models
- ✅ **Download script created**: `tools/download_required_models.py`
- ⚠️ **You need to run it**: Requires internet, disk space, time
- ⚠️ **Or download manually**: More time-consuming

### Integration Testing
- ⏳ **Test files**: I can create now
- ⏳ **Execution**: Requires models to be downloaded
- ⏳ **Test files**: You've already provided (TBX, XLIFF, TMX)

### Recommendation
1. **You run**: `python tools/download_required_models.py` (1-3 hours)
2. **I create**: Integration test files (ready now)
3. **We run**: Integration tests together (after models downloaded)

---

**Question**: Would you like me to:
1. Create the integration test files now (ready for when models are downloaded)?
2. Create alternative tests using smaller models?
3. Wait for you to download models first?

Let me know your preference!
