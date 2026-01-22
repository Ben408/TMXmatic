# Integration Testing Requirements - Summary

**Quick Answer**: You need to download models (I've created the script)

---

## 1-4. Model Download

### Can I Download Models?

**Short Answer**: **I've created the script, but YOU need to run it.**

### Why You Need to Run It

1. **Time**: Downloads take 1-3 hours (24GB model)
2. **Internet**: Requires your connection
3. **Disk Space**: Needs ~25GB on your machine
4. **Interactive**: May need HuggingFace token

### What I've Done

✅ **Created download script**: `tools/download_required_models.py`
- Automated download
- Progress reporting
- Error handling
- Verification

✅ **Created verification script**: `tools/verify_models.py`
- Check model status
- Report what's missing

### What You Need to Do

**Run this command**:
```bash
cd "F:\LLM Quality Module for TMXmatic"
.venv\Scripts\Activate.ps1
python tools/download_required_models.py
```

**Time**: 1-3 hours (mostly waiting for downloads)

**Requirements**:
- Internet connection
- ~25GB disk space
- HuggingFace account (may need token)

---

## 5. Full Integration Testing Requirements

### What's Needed

#### Models (You Download)
1. **translategemma-12b-it** (24GB) - **REQUIRED**
   - Main translation model
   - Download via script

2. **SBERT Multilingual** (0.4GB) - **REQUIRED**
   - Similarity scoring
   - Auto-downloads or via script

3. **COMET models** (1GB total) - **OPTIONAL**
   - Quality estimation enhancement
   - Can skip for basic testing

#### Test Files (You've Provided)
- ✅ **XLIFF**: `C:\Users\bjcor\Desktop\Sage Local\SW XLIFF\error message.xlf`
- ✅ **TBX**: `C:\Users\bjcor\Desktop\Sage Local\SDMO Glossary\SDMO_multilingual_merged.tbx`
- ✅ **TMX**: `C:\Users\bjcor\Desktop\TMXmatic\Test_files`

#### Integration Tests (I've Created)
- ✅ `tests/integration/test_full_workflow_real_files.py`
- ✅ `tests/integration/test_model_loading.py`
- ✅ Ready to run once models downloaded

---

## Integration Tests Created

### Test 1: Model Loading (`test_model_loading.py`)
**Tests**:
- SBERT model loading and encoding
- translategemma model loading
- Actual translation generation
- TQE engine with models

**Requires**: Models downloaded

### Test 2: Full Workflow (`test_full_workflow_real_files.py`)
**Tests**:
- XLIFF-only workflow
- XLIFF + TMX workflow
- XLIFF + TBX workflow
- XLIFF + TMX + TBX workflow (complete)

**Requires**: Models + your test files

---

## Complete Integration Testing Checklist

### Prerequisites
- [ ] Models downloaded (run `tools/download_required_models.py`)
- [ ] Models verified (run `tools/verify_models.py`)
- [ ] Test files accessible (you've provided these)
- [ ] GPU available (optional, CPU works but slower)

### Test Execution
- [ ] Run model loading tests: `pytest tests/integration/test_model_loading.py -v -m requires_models`
- [ ] Run full workflow tests: `pytest tests/integration/test_full_workflow_real_files.py -v -m requires_models`
- [ ] Verify output XLIFF files
- [ ] Check quality scores in metadata
- [ ] Verify match rates written correctly

### Expected Results
- ✅ Models load successfully
- ✅ Translations generated
- ✅ Quality scores calculated
- ✅ Match rates written to XLIFF
- ✅ Metadata preserved
- ✅ Output files valid XLIFF

---

## Timeline

### Option 1: Download Models Now
1. **You**: Run download script (1-3 hours)
2. **Me**: Integration tests already created
3. **Together**: Run tests immediately after download

**Total Time**: 1-3 hours (download) + 30 minutes (testing)

### Option 2: Test Without Full Models
1. **Me**: Create tests with smaller models or enhanced mocks
2. **You**: Test with full models later in staging

**Total Time**: 1-2 hours (test creation) + testing time

---

## Recommendation

**I recommend Option 1**:
1. You run the download script (can run in background)
2. Integration tests are ready
3. Run tests after download completes

**The download script is ready** - just needs you to execute it!

---

## Files Created

1. ✅ `tools/download_required_models.py` - Download script
2. ✅ `tools/verify_models.py` - Verification script
3. ✅ `tests/integration/test_model_loading.py` - Model loading tests
4. ✅ `tests/integration/test_full_workflow_real_files.py` - Full workflow tests
5. ✅ `INTEGRATION_TESTING_PLAN.md` - Detailed plan
6. ✅ `MODEL_DOWNLOAD_GUIDE.md` - Download guide
7. ✅ `INTEGRATION_TESTING_REQUIREMENTS.md` - This file

---

**Status**: ✅ **Ready for you to download models and run integration tests**
