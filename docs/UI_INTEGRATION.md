# UI Integration Guide

Complete guide for the UI components and integration with TMXmatic.

---

## Overview

The LLM Quality Module UI is fully integrated into TMXmatic, providing:
- GPU status monitoring
- Model management
- Translation interface
- Progress tracking
- Quality results viewing

---

## Components Created

### 1. API Client (`lib/api/gpu-translation.ts`)
- TypeScript client for all GPU translation endpoints
- Type-safe interfaces
- Error handling

### 2. GPU Status Display (`components/gpu-status.tsx`)
- Real-time GPU detection
- CUDA availability
- Memory information
- CPU fallback warnings

### 3. Model Management (`components/model-management.tsx`)
- List available models
- Download with progress
- Required vs optional distinction
- Status indicators

### 4. Translation Panel (`components/translation-panel.tsx`)
- Language selection
- Optional TMX/TBX file selection
- Configuration options
- Progress and statistics

### 5. Progress Tracker (`components/translation-progress.tsx`)
- Real-time progress bar
- Segment statistics
- Time tracking

### 6. Quality Results Viewer (`components/quality-results.tsx`)
- Quality score display
- Filtering by threshold
- Detailed metrics table
- Export functionality

---

## Integration Points

### Workspace Integration
The UI is integrated into `tmx-workspace.tsx` with:
- **New Tabs**: Workspace, GPU Translation, Models
- **GPU Status**: Displayed in GPU Translation tab
- **Translation Panel**: Available when XLIFF file selected
- **Model Management**: Separate tab for model operations

### Operations Added
Three new operations added to `OPERATIONS` array:
- `gpu_translate` - Translate with GPU
- `gpu_translate_with_tmx` - Translate with GPU + TMX
- `gpu_translate_with_tbx` - Translate with GPU + TBX

---

## User Workflow

### 1. Check GPU Status
1. Open "GPU Translation" tab
2. View GPU availability and memory
3. Check if models are downloaded

### 2. Manage Models
1. Open "Models" tab
2. View available models
3. Download required models
4. Monitor download progress

### 3. Translate Files
1. Select XLIFF file in workspace
2. Open "GPU Translation" tab
3. Configure:
   - Source/target languages
   - Optional TMX file
   - Optional TBX file
   - Profile (optional)
   - Number of candidates
   - Fuzzy threshold
4. Click "Translate"
5. Monitor progress
6. View results and statistics

### 4. Review Quality
1. View quality scores per segment
2. Filter by quality threshold
3. Export quality report

---

## API Endpoints Used

- `GET /api/local_gpu/gpu/status` - GPU status
- `GET /api/local_gpu/models/list` - List models
- `POST /api/local_gpu/models/download` - Download model
- `POST /api/local_gpu/translate` - Translate XLIFF
- `GET /api/local_gpu/translate/download` - Download result

---

## File Structure

```
dist/New_UI/
├── lib/
│   └── api/
│       └── gpu-translation.ts          ✅ Created
├── components/
│   ├── gpu-status.tsx                  ✅ Created
│   ├── model-management.tsx             ✅ Created
│   ├── translation-panel.tsx            ✅ Created
│   ├── translation-progress.tsx        ✅ Created
│   ├── quality-results.tsx              ✅ Created
│   └── tmx-workspace.tsx               ✅ Updated
```

---

## Features

### ✅ GPU Status
- Real-time detection
- Memory information
- CUDA availability
- CPU fallback warnings

### ✅ Model Management
- Model listing
- Download functionality
- Progress tracking
- Status indicators

### ✅ Translation Interface
- Language selection
- File selection (XLIFF, TMX, TBX)
- Configuration options
- Progress tracking
- Statistics display

### ✅ Quality Results
- Score visualization
- Filtering
- Detailed metrics
- Export capability

### ✅ Error Handling
- API error handling
- User-friendly messages
- Toast notifications
- Loading states

---

## Styling

- Uses shadcn/ui components for consistency
- Matches existing TMXmatic UI style
- Responsive design
- Accessible (WCAG compliance)

---

## Testing UI

### Manual Testing
1. Start TMXmatic: `python launcher.py`
2. Open browser: `http://localhost:3000`
3. Test each component:
   - GPU status display
   - Model management
   - Translation workflow
   - Quality results

### Automated Testing
- Component tests (to be added)
- Integration tests (to be added)
- E2E tests (to be added)

---

## Original Documentation (Archived)
- `docs/archive/UI_INTEGRATION_GUIDE.md` - Original guide
- `docs/archive/UI_INTEGRATION_COMPLETE.md` - Completion status
- `docs/archive/UI_IMPLEMENTATION_SUMMARY.md` - Implementation summary

---

**Status**: ✅ UI Integration Complete - All components created and integrated
