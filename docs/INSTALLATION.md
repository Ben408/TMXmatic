# Installation & Integration Guide

Complete guide for installing and integrating the LLM Quality Module with TMXmatic.

---

## Quick Start (5 Minutes)

### Step 1: Copy Module Files
```powershell
Copy-Item -Path "F:\LLM Quality Module for TMXmatic\local_gpu_translation" -Destination "C:\Users\bjcor\Desktop\TMXmatic\" -Recurse
Copy-Item -Path "F:\LLM Quality Module for TMXmatic\shared" -Destination "C:\Users\bjcor\Desktop\TMXmatic\" -Recurse
```

### Step 2: Install Dependencies
```powershell
cd "C:\Users\bjcor\Desktop\TMXmatic"
.venv\Scripts\Activate.ps1
pip install torch transformers sentence-transformers bert-score tqdm rapidfuzz huggingface-hub comet-ml scikit-learn
```

### Step 3: Register Flask Blueprint

Edit `C:\Users\bjcor\Desktop\TMXmatic\app.py`:

**Add after imports (around line 20):**
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

**Add after app initialization (around line 80):**
```python
# Register LLM Quality Module blueprint
if LLM_QUALITY_MODULE_AVAILABLE:
    app.register_blueprint(local_gpu_bp, url_prefix='/api/local_gpu')
    logger.info("LLM Quality Module API endpoints registered")
```

### Step 4: Test
```powershell
python launcher.py
# In another terminal:
curl http://localhost:5000/api/local_gpu/gpu/status
```

---

## Detailed Installation

### Prerequisites
- Python 3.11+
- CUDA-capable GPU (8GB+ VRAM recommended)
- Windows 10/11
- ~25GB disk space for models
- Internet connection for model downloads

### Installation Options

#### Option A: Copy Entire Module (Recommended)
```powershell
Copy-Item -Path "F:\LLM Quality Module for TMXmatic\local_gpu_translation" -Destination "C:\Users\bjcor\Desktop\TMXmatic\" -Recurse
Copy-Item -Path "F:\LLM Quality Module for TMXmatic\shared" -Destination "C:\Users\bjcor\Desktop\TMXmatic\" -Recurse
```

#### Option B: Symlink (Development)
```powershell
mklink /D "C:\Users\bjcor\Desktop\TMXmatic\local_gpu_translation" "F:\LLM Quality Module for TMXmatic\local_gpu_translation"
mklink /D "C:\Users\bjcor\Desktop\TMXmatic\shared" "F:\LLM Quality Module for TMXmatic\shared"
```

### Dependencies

Add to `C:\Users\bjcor\Desktop\TMXmatic\other\requirements.txt`:
```txt
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

---

## Model Management

### Required Models
- **translategemma-12b-it** (24GB) - Main translation model
- **SBERT Multilingual** (0.4GB) - Similarity scoring

### Optional Models
- **COMET Reference** (0.5GB) - Quality estimation
- **COMET-QE** (0.5GB) - Quality estimation without reference

### Downloading Models

**Automated (Recommended):**
```bash
cd "F:\LLM Quality Module for TMXmatic"
.venv\Scripts\Activate.ps1
python tools/download_required_models.py
```

**Time**: 1-3 hours (mostly waiting for 24GB model)

**Verify:**
```bash
python tools/verify_models.py
```

### Model Storage

Models are stored in `Models/` directory by default. You can configure the path in `ModelManager` to use a shared location.

---

## Integration Status

### ✅ Backend (Ready)
- Flask API endpoints implemented
- Blueprint ready for registration
- All translation logic complete
- Model management functional

### ✅ UI (Complete)
- GPU status display
- Model management interface
- Translation panel
- Progress tracking
- Quality results viewer

### What Works After Integration

**API Endpoints** (work immediately):
- `GET /api/local_gpu/gpu/status` - Check GPU availability
- `GET /api/local_gpu/models/list` - List models
- `POST /api/local_gpu/models/download` - Download models
- `POST /api/local_gpu/translate` - Translate XLIFF files
- `GET /api/local_gpu/translate/download` - Download results

**UI Features**:
- GPU Translation tab in sidebar
- Model Management tab
- Translation panel with configuration
- Real-time progress tracking

---

## Testing the Installation

### Test API Endpoints
```bash
# GPU Status
curl http://localhost:5000/api/local_gpu/gpu/status

# List Models
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

### Test UI
1. Start TMXmatic: `python launcher.py`
2. Open browser to `http://localhost:3000`
3. Check "GPU Translation" tab for GPU status
4. Check "Models" tab for model management
5. Upload XLIFF file and test translation

---

## Troubleshooting

### Module Not Available
- Check that files were copied correctly
- Verify dependencies are installed
- Check Python path includes module directories

### GPU Not Detected
- Verify CUDA is installed
- Check GPU drivers are up to date
- Module will fall back to CPU (slower)

### Models Not Downloading
- Check internet connection
- Verify disk space (25GB+)
- Check HuggingFace token if required
- Try manual download from HuggingFace

### API Endpoints Not Working
- Verify blueprint is registered in `app.py`
- Check Flask server is running
- Verify CORS is enabled
- Check logs for errors

---

## Next Steps

1. **Download Models**: Use UI or `tools/download_required_models.py`
2. **Test Translation**: Use UI or API endpoints
3. **Configure Profiles**: Set up client-specific profiles
4. **Review Quality Results**: Check quality scores in output XLIFF

---

## Additional Resources

- **API Reference**: See `docs/API_REFERENCE.md`
- **Architecture**: See `docs/ARCHITECTURE.md`
- **Testing**: See `docs/TESTING.md`
- **UI Integration**: See `docs/UI_INTEGRATION.md`

---

**Status**: ✅ Ready for installation and use
