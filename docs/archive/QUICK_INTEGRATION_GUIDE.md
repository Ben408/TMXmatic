# Quick Integration Guide

**Goal**: Get the LLM Quality Module working with your TMXmatic installation

---

## 5-Minute Backend Integration

### Step 1: Copy Module Files

```powershell
# Copy module directories
Copy-Item -Path "F:\LLM Quality Module for TMXmatic\local_gpu_translation" -Destination "C:\Users\bjcor\Desktop\TMXmatic\" -Recurse
Copy-Item -Path "F:\LLM Quality Module for TMXmatic\shared" -Destination "C:\Users\bjcor\Desktop\TMXmatic\" -Recurse
```

### Step 2: Install Dependencies

```powershell
cd "C:\Users\bjcor\Desktop\TMXmatic"
.venv\Scripts\Activate.ps1
pip install torch transformers sentence-transformers bert-score tqdm rapidfuzz huggingface-hub comet-ml scikit-learn
```

### Step 3: Register Blueprint

**Edit `C:\Users\bjcor\Desktop\TMXmatic\app.py`**:

**Add after line 20** (after other imports):
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

**Add after line 80** (after `CORS(app, ...)`):
```python
# Register LLM Quality Module blueprint
if LLM_QUALITY_MODULE_AVAILABLE:
    app.register_blueprint(local_gpu_bp, url_prefix='/api/local_gpu')
    logger.info("LLM Quality Module API endpoints registered")
```

### Step 4: Test

```powershell
# Start TMXmatic
python launcher.py

# In another terminal, test:
curl http://localhost:5000/api/local_gpu/gpu/status
```

**If you see GPU status JSON, it's working!**

---

## What You Get

### ✅ Backend API (Works Immediately)
- `GET /api/local_gpu/gpu/status` - Check GPU
- `GET /api/local_gpu/models/list` - List models
- `POST /api/local_gpu/models/download` - Download models
- `POST /api/local_gpu/translate` - Translate XLIFF

### ⚠️ UI (Needs to be Built)
- UI components not created yet
- Need to add React/Next.js components
- See `UI_INTEGRATION_GUIDE.md` for details

---

## Test Translation (Backend Only)

### Using curl:
```bash
curl -X POST http://localhost:5000/api/local_gpu/translate \
  -H "Content-Type: application/json" \
  -d '{
    "xliff_path": "C:/Users/bjcor/Desktop/Sage Local/SW XLIFF/error message.xlf",
    "src_lang": "en",
    "tgt_lang": "fr"
  }'
```

### Using Python:
```python
import requests

response = requests.post('http://localhost:5000/api/local_gpu/translate', json={
    'xliff_path': r'C:\Users\bjcor\Desktop\Sage Local\SW XLIFF\error message.xlf',
    'src_lang': 'en',
    'tgt_lang': 'fr'
})
print(response.json())
```

---

## Next Steps

1. **Download models**: `python tools/download_required_models.py` (from module directory)
2. **Test translation**: Use curl or Python script above
3. **Build UI**: See `UI_INTEGRATION_GUIDE.md` for component creation

---

**Status**: ✅ Backend ready | ⚠️ UI needs development
