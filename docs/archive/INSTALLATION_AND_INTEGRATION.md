# Installation and Integration Guide

**Question**: Can I install and use the module with my local TMXmatic installation? Will all new functions become available through the UI?

**Short Answer**: 
- ✅ **Backend**: Ready to integrate (just register the blueprint)
- ⚠️ **UI**: Needs to be implemented (components not created yet)

---

## Current Status

### ✅ Backend (Ready)
- ✅ Flask API endpoints created
- ✅ Blueprint ready for registration
- ✅ All translation logic implemented
- ✅ Model management ready

### ⚠️ UI (Not Yet Implemented)
- ⚠️ UI components need to be created
- ⚠️ Integration with existing TMXmatic UI needed
- ⚠️ API calls from frontend need to be added

---

## Installation Steps

### Step 1: Copy Module to TMXmatic

**Option A: Copy Entire Module** (Recommended)
```bash
# Copy the module directory to your TMXmatic installation
cp -r "F:\LLM Quality Module for TMXmatic\local_gpu_translation" "C:\Users\bjcor\Desktop\TMXmatic\"
cp -r "F:\LLM Quality Module for TMXmatic\shared" "C:\Users\bjcor\Desktop\TMXmatic\"
```

**Option B: Symlink** (Development)
```bash
# Create symlinks (Windows)
mklink /D "C:\Users\bjcor\Desktop\TMXmatic\local_gpu_translation" "F:\LLM Quality Module for TMXmatic\local_gpu_translation"
mklink /D "C:\Users\bjcor\Desktop\TMXmatic\shared" "F:\LLM Quality Module for TMXmatic\shared"
```

### Step 2: Install Dependencies

Add to `C:\Users\bjcor\Desktop\TMXmatic\other\requirements.txt`:

```txt
# LLM Quality Module Dependencies
torch>=2.0.0
transformers>=4.30.0
sentence-transformers>=2.2.0
bert-score>=0.3.13
tqdm>=4.65.0
rapidfuzz>=3.0.0
huggingface-hub>=0.16.0
comet-ml>=3.0.0
scikit-learn>=1.3.0
```

Then install:
```bash
cd "C:\Users\bjcor\Desktop\TMXmatic"
.venv\Scripts\Activate.ps1
pip install -r other/requirements.txt
```

### Step 3: Register Flask Blueprint

**Edit `C:\Users\bjcor\Desktop\TMXmatic\app.py`**:

Add after the imports (around line 20):
```python
# LLM Quality Module
try:
    from local_gpu_translation.api.endpoints import local_gpu_bp
    LLM_QUALITY_MODULE_AVAILABLE = True
    logger.info("LLM Quality Module loaded successfully")
except ImportError as e:
    LLM_QUALITY_MODULE_AVAILABLE = False
    logger.warning(f"LLM Quality Module not available: {e}")
```

Add after app initialization (around line 80, after `CORS(app, ...)`):
```python
# Register LLM Quality Module blueprint (if available)
if LLM_QUALITY_MODULE_AVAILABLE:
    app.register_blueprint(local_gpu_bp, url_prefix='/api/local_gpu')
    logger.info("LLM Quality Module API endpoints registered at /api/local_gpu")
```

### Step 4: Download Models

```bash
cd "F:\LLM Quality Module for TMXmatic"
.venv\Scripts\Activate.ps1
python tools/download_required_models.py
```

**Note**: Models will be downloaded to `F:\LLM Quality Module for TMXmatic\Models\` by default. You may want to configure the path in `ModelManager` to use a shared location.

### Step 5: Verify Installation

**Test API endpoints**:
```bash
# Start TMXmatic
cd "C:\Users\bjcor\Desktop\TMXmatic"
python launcher.py

# In another terminal, test GPU status
curl http://localhost:5000/api/local_gpu/gpu/status

# Test model list
curl http://localhost:5000/api/local_gpu/models/list
```

---

## What Works After Installation

### ✅ Backend API (Ready)
Once you register the blueprint, these endpoints are available:

- `GET /api/local_gpu/gpu/status` - Check GPU availability
- `GET /api/local_gpu/models/list` - List available models
- `POST /api/local_gpu/models/download` - Download models
- `POST /api/local_gpu/translate` - Translate XLIFF files
- `GET /api/local_gpu/translate/download` - Download translated files

**You can test these with curl, Postman, or any HTTP client.**

### ⚠️ UI Components (Need to be Created)
The UI components are **not yet implemented**. You'll need to:

1. **Create React/Next.js components** (see `UI_INTEGRATION_GUIDE.md`)
2. **Add API integration** in the frontend
3. **Update existing UI** to show new options

---

## What Needs to Be Done for Full UI Integration

### Phase 1: Basic Integration (Minimal)

**1. Add Translation Button** to existing UI:
- Add button in operations panel
- Call `/api/local_gpu/translate` endpoint
- Show results

**2. Add GPU Status Display**:
- Show GPU availability on main page
- Warn if GPU not available

**Estimated Time**: 2-4 hours

### Phase 2: Full Integration (Complete)

**1. Translation Panel Component**:
- File upload (XLIFF, TMX, TBX)
- Language selection
- Profile selection
- Progress tracking
- Results display

**2. Model Management UI**:
- List models
- Download models
- Show download progress
- Delete models

**3. Quality Results Viewer**:
- Display quality scores
- Filter by threshold
- Export reports

**Estimated Time**: 1-2 days

---

## Quick Start: Test Backend Only

If you want to test the backend **without UI**, you can:

### 1. Register Blueprint (as above)

### 2. Test with curl/Postman

```bash
# Check GPU status
curl http://localhost:5000/api/local_gpu/gpu/status

# List models
curl http://localhost:5000/api/local_gpu/models/list

# Translate (example)
curl -X POST http://localhost:5000/api/local_gpu/translate \
  -H "Content-Type: application/json" \
  -d '{
    "xliff_path": "path/to/file.xlf",
    "src_lang": "en",
    "tgt_lang": "fr"
  }'
```

### 3. Use Python Script

Create a simple test script:
```python
import requests

# Check GPU
response = requests.get('http://localhost:5000/api/local_gpu/gpu/status')
print(response.json())

# Translate
response = requests.post('http://localhost:5000/api/local_gpu/translate', json={
    'xliff_path': 'path/to/file.xlf',
    'src_lang': 'en',
    'tgt_lang': 'fr'
})
print(response.json())
```

---

## Integration Checklist

### Backend Integration
- [ ] Copy module to TMXmatic directory
- [ ] Install dependencies
- [ ] Register Flask blueprint in `app.py`
- [ ] Download models
- [ ] Test API endpoints

### UI Integration (Future)
- [ ] Create translation panel component
- [ ] Add GPU status display
- [ ] Create model management UI
- [ ] Add quality results viewer
- [ ] Update operations panel
- [ ] Add progress tracking
- [ ] Test complete workflow

---

## Current Limitations

### What Works Now
- ✅ Backend API endpoints
- ✅ Model management
- ✅ Translation logic
- ✅ Quality estimation
- ✅ GPU detection

### What Doesn't Work Yet
- ⚠️ UI components (need to be created)
- ⚠️ Frontend API integration (needs to be added)
- ⚠️ User-friendly file upload (needs UI)
- ⚠️ Progress visualization (needs UI)

---

## Recommendation

### Option 1: Backend Only (Quick)
1. Register blueprint
2. Test with curl/Postman
3. Use Python scripts for translation
4. **UI can be added later**

**Time**: 30 minutes

### Option 2: Full Integration (Complete)
1. Register blueprint
2. Create UI components
3. Integrate with existing UI
4. Test complete workflow

**Time**: 1-2 days

---

## Next Steps

### Immediate (You Can Do Now)
1. **Copy module** to TMXmatic directory
2. **Install dependencies**
3. **Register blueprint** in `app.py`
4. **Download models**
5. **Test API endpoints** with curl/Postman

### Future (UI Development)
1. **Create UI components** (see `UI_INTEGRATION_GUIDE.md`)
2. **Add API calls** in frontend
3. **Update existing UI** to show new options
4. **Test complete workflow**

---

## Summary

### Can You Install It?
**Yes!** The backend is ready. Just:
1. Copy module files
2. Install dependencies
3. Register blueprint
4. Download models

### Will Functions Be Available in UI?
**Not automatically.** The backend API works, but:
- UI components need to be created
- Frontend needs to call the API
- Integration with existing UI needed

**However**, you can:
- ✅ Test backend with curl/Postman
- ✅ Use Python scripts
- ✅ Build UI components later

---

**Status**: ✅ **Backend ready for integration** | ⚠️ **UI needs to be built**
