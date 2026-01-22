# Model Download Guide

**Status**: ✅ Download script ready  
**Action Required**: You need to run the download script

---

## Can I Download Models?

### ✅ Yes, I Can Create the Script
- ✅ Download script created: `tools/download_required_models.py`
- ✅ Model verification script: `tools/verify_models.py`
- ✅ Integration test files: Created and ready

### ⚠️ You Need to Run It
**I cannot execute long-running downloads**, but the script is ready for you to run.

**Why you need to run it**:
1. **Time**: Downloads take 1-3 hours (24GB model)
2. **Internet**: Requires stable connection
3. **Disk Space**: Needs ~25GB free space
4. **Interactive**: May need HuggingFace token input

---

## Quick Start

### Step 1: Run Download Script

```bash
cd "F:\LLM Quality Module for TMXmatic"
.venv\Scripts\Activate.ps1
python tools/download_required_models.py
```

**What it does**:
- Checks disk space
- Downloads required models (translategemma-12b-it, SBERT)
- Optionally downloads COMET models
- Verifies downloads
- Reports status

**Time**: 1-3 hours (mostly waiting)

### Step 2: Verify Models

```bash
python tools/verify_models.py
```

Should show all required models as `[OK]`.

### Step 3: Run Integration Tests

```bash
pytest tests/integration/ -v -m requires_models
```

---

## Model Details

### Required Models

#### 1. translategemma-12b-it
- **Registry ID**: `translategemma-12b-it`
- **HuggingFace**: `google/translategemma-12b-it`
- **Size**: 24GB
- **Time**: ~2-3 hours (depending on connection)
- **Required**: Yes

#### 2. SBERT Multilingual
- **Registry ID**: `sbert-multilingual`
- **HuggingFace**: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- **Size**: 0.4GB
- **Time**: ~5-10 minutes
- **Required**: Yes

### Optional Models

#### 3. COMET Reference
- **Registry ID**: `comet-22`
- **HuggingFace**: `Unbabel/wmt22-comet-da`
- **Size**: 0.5GB
- **Time**: ~10-15 minutes
- **Required**: No (enhances quality estimation)

#### 4. COMET-QE
- **Registry ID**: `comet-qe-22`
- **HuggingFace**: `Unbabel/wmt22-cometkiwi-da`
- **Size**: 0.5GB
- **Time**: ~10-15 minutes
- **Required**: No (enhances quality estimation)

---

## Download Options

### Option 1: Automated (Recommended)

**Run**: `python tools/download_required_models.py`

**Pros**:
- ✅ Handles everything automatically
- ✅ Verifies downloads
- ✅ Reports progress
- ✅ Can resume if interrupted

**Cons**:
- ⚠️ Requires your time (1-3 hours)
- ⚠️ Requires internet connection
- ⚠️ Requires disk space

### Option 2: Manual Download

**Steps**:
1. Visit HuggingFace model pages
2. Download using HuggingFace CLI or web
3. Place in `Models/` directory
4. Run verification script

**Pros**:
- ✅ More control
- ✅ Can download in stages

**Cons**:
- ⚠️ More time-consuming
- ⚠️ Manual file management

### Option 3: Use Smaller Test Models

**Alternative**: Use smaller models for testing, download full models later

**Pros**:
- ✅ Faster for testing
- ✅ Less disk space

**Cons**:
- ⚠️ Not production-ready
- ⚠️ Different results

---

## What I've Prepared

### ✅ Created
1. **Download Script**: `tools/download_required_models.py`
   - Automated download
   - Progress reporting
   - Error handling

2. **Verification Script**: `tools/verify_models.py`
   - Check model status
   - Report what's missing

3. **Integration Tests**: 
   - `tests/integration/test_full_workflow_real_files.py`
   - `tests/integration/test_model_loading.py`
   - Ready to run once models downloaded

4. **Documentation**:
   - `INTEGRATION_TESTING_PLAN.md`
   - `MODEL_DOWNLOAD_GUIDE.md` (this file)

### ⏳ Waiting For
- **You to run**: `python tools/download_required_models.py`
- **Models to download**: 1-3 hours
- **Then**: Run integration tests

---

## Full Integration Testing Requirements

### What's Needed

1. **Models** (You need to download):
   - ✅ translategemma-12b-it (24GB) - **REQUIRED**
   - ✅ SBERT (0.4GB) - **REQUIRED**
   - ⚠️ COMET models (1GB total) - **OPTIONAL**

2. **Test Files** (You've provided):
   - ✅ XLIFF: `C:\Users\bjcor\Desktop\Sage Local\SW XLIFF\error message.xlf`
   - ✅ TBX: `C:\Users\bjcor\Desktop\Sage Local\SDMO Glossary\SDMO_multilingual_merged.tbx`
   - ✅ TMX: `C:\Users\bjcor\Desktop\TMXmatic\Test_files`

3. **Integration Tests** (I've created):
   - ✅ `test_full_workflow_real_files.py`
   - ✅ `test_model_loading.py`
   - ⏳ Ready to run after models downloaded

### Integration Tests to Run

#### Test 1: Model Loading
```bash
pytest tests/integration/test_model_loading.py -v -m requires_models
```
**Tests**: Model loading, basic inference, SBERT encoding

#### Test 2: Full Workflow
```bash
pytest tests/integration/test_full_workflow_real_files.py -v -m requires_models
```
**Tests**: Complete translation workflow with your test files

#### Test 3: All Integration Tests
```bash
pytest tests/integration/ -v -m requires_models
```

---

## Recommendation

### My Recommendation

1. **You run**: `python tools/download_required_models.py`
   - Start it and let it run (1-3 hours)
   - Can run in background

2. **I've already created**:
   - ✅ Download script
   - ✅ Integration test files
   - ✅ Verification tools

3. **After download**:
   - Verify: `python tools/verify_models.py`
   - Run tests: `pytest tests/integration/ -v -m requires_models`

### Alternative: Test Without Full Models

If downloading 24GB is not feasible now, I can:
1. Create tests using smaller models
2. Enhance mocking for integration tests
3. Test with full models later in staging

---

## Summary

### Models
- ✅ **Script ready**: `tools/download_required_models.py`
- ⚠️ **You need to run it**: Requires 1-3 hours, internet, disk space
- ✅ **I can't run it**: Long-running downloads require your execution

### Integration Testing
- ✅ **Test files created**: Ready to run
- ⚠️ **Requires models**: Need to download first
- ✅ **Test files provided**: You've already given us XLIFF, TBX, TMX

### Next Steps
1. **You**: Run `python tools/download_required_models.py` (1-3 hours)
2. **Me**: Already created integration tests (ready now)
3. **Together**: Run integration tests after models downloaded

---

**Answer**: I've created the download script, but **you need to run it** because:
- It's a long-running process (1-3 hours)
- Requires your internet connection
- May need interactive input (HuggingFace token)

The script is ready - just run it when convenient!
