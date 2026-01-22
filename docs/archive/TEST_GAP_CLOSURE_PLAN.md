# Test Gap Closure Plan

**Date**: 2025-01-XX  
**Current Status**: 202 tests passing, 80-97% coverage for tested components

---

## Identified Gaps Summary

### Critical Gaps 🔴 (Priority 1)
1. Model-dependent component testing
2. End-to-end translation pipeline
3. Large file handling
4. Error recovery with real failures
5. Concurrent processing

### Important Gaps 🟡 (Priority 2)
1. Model download functionality
2. COMET model integration
3. UQLM integration
4. Profile management edge cases

---

## Gap Closure Strategy

### Phase 1: Critical Gaps (Week 1)

#### 1.1 Model Loading Integration Tests
**Status**: ⏳ Pending  
**Approach**: Use small test models or mock model loading more comprehensively

**Tests to Add**:
```python
# tests/integration/test_model_loading.py
def test_candidate_generator_loads_model():
    """Test actual model loading (with small test model)"""
    pass

def test_model_memory_management():
    """Test memory management with loaded model"""
    pass
```

**Estimated Effort**: 2-3 days

#### 1.2 End-to-End Translation Test
**Status**: ⏳ Pending  
**Approach**: Use provided test files (XLIFF, TMX, TBX)

**Tests to Add**:
```python
# tests/integration/test_full_workflow.py
def test_full_translation_workflow_with_files():
    """Test complete workflow with real XLIFF/TMX/TBX files"""
    # Use: 
    # - XLIFF: "C:\Users\bjcor\Desktop\Sage Local\SW XLIFF\error message.xlf"
    # - TBX: "C:\Users\bjcor\Desktop\Sage Local\SDMO Glossary\SDMO_multilingual_merged.tbx"
    # - TMX: "C:\Users\bjcor\Desktop\TMXmatic\Test_files"
    pass
```

**Estimated Effort**: 1-2 days

#### 1.3 Large File Handling Tests
**Status**: ⏳ Pending  
**Approach**: Generate or use large test files

**Tests to Add**:
```python
# tests/integration/test_large_files.py
def test_large_xliff_processing():
    """Test processing XLIFF with 1000+ segments"""
    pass

def test_large_tmx_matching():
    """Test TMX matching with 10,000+ entries"""
    pass
```

**Estimated Effort**: 1 day

#### 1.4 Error Recovery Tests
**Status**: ⏳ Pending  
**Approach**: Simulate real failure scenarios

**Tests to Add**:
```python
# tests/integration/test_error_recovery.py
def test_gpu_oom_recovery():
    """Test recovery from GPU out-of-memory"""
    pass

def test_partial_result_saving():
    """Test saving partial results on error"""
    pass
```

**Estimated Effort**: 1-2 days

#### 1.5 Concurrent Processing Tests
**Status**: ⏳ Pending  
**Approach**: Test thread safety

**Tests to Add**:
```python
# tests/integration/test_concurrency.py
def test_concurrent_translation():
    """Test concurrent translation requests"""
    pass
```

**Estimated Effort**: 1 day

### Phase 2: Important Gaps (Week 2)

#### 2.1 Model Download Tests
**Status**: ⏳ Pending  
**Tests to Add**:
- Actual HuggingFace download
- Download progress tracking
- Download failure recovery

#### 2.2 COMET Integration Tests
**Status**: ⏳ Pending  
**Tests to Add**:
- COMET model loading
- COMET scoring with real models
- COMET batch processing

#### 2.3 UQLM Integration Tests
**Status**: ⏳ Pending  
**Tests to Add**:
- UQLM installation verification
- Hallucination detection
- UQLM error handling

---

## Implementation Notes

### Test File Locations
User-provided test files:
- **TBX**: `C:\Users\bjcor\Desktop\Sage Local\SDMO Glossary\SDMO_multilingual_merged.tbx`
- **XLIFF**: `C:\Users\bjcor\Desktop\Sage Local\SW XLIFF\error message.xlf`
- **TMX**: `C:\Users\bjcor\Desktop\TMXmatic\Test_files`

### Model Testing Strategy
- Use small test models for integration tests
- Mock model loading for unit tests (current approach)
- Test actual model loading when models available

### Large File Generation
- Create script to generate large test files
- Use provided test files as templates
- Test with various sizes (100, 500, 1000, 5000 segments)

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Model loading integration tests passing
- [ ] End-to-end workflow test passing with real files
- [ ] Large file handling tests passing
- [ ] Error recovery tests passing
- [ ] Concurrent processing tests passing

### Phase 2 Complete When:
- [ ] Model download tests passing
- [ ] COMET integration tests passing
- [ ] UQLM integration tests passing

---

## Timeline

- **Week 1**: Critical gaps (Priority 1)
- **Week 2**: Important gaps (Priority 2)
- **Week 3**: Review and refinement

---

## Current Test Status

✅ **Excellent Foundation**
- 202 tests passing
- 80-97% coverage for tested components
- Good test structure and organization

⏳ **Gaps to Address**
- Model-dependent functionality
- End-to-end scenarios
- Large file handling
- Real failure scenarios

---

**Status**: Plan created, ready for implementation  
**Next Action**: Begin Phase 1 gap closure
