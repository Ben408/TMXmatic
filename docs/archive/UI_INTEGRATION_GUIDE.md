# UI Integration Guide

**Module**: LLM Quality Module for TMXmatic  
**UI Framework**: Next.js/React (TypeScript)  
**Status**: ⏳ **PENDING IMPLEMENTATION**

---

## Overview

This guide outlines the UI components and integration points needed to surface the LLM Quality Module functionality in the TMXmatic UI.

## Required UI Components

### 1. Translation Panel Component

**File**: `components/translation-panel.tsx` (or similar)

**Features**:
- File upload (XLIFF, TMX, TBX)
- Language pair selection
- Profile selection dropdown
- Translation options (number of candidates, fuzzy threshold)
- Start/Stop translation button
- Progress visualization

**API Integration**:
```typescript
// POST /local_gpu/translate
interface TranslateRequest {
  xliff_path: string;
  tmx_path?: string;
  tbx_path?: string;
  src_lang: string;
  tgt_lang: string;
  profile_name?: string;
}

interface TranslateResponse {
  status: 'success' | 'error';
  output_path: string;
  statistics: {
    total: number;
    processed: number;
    exact_matches: number;
    fuzzy_repairs: number;
    new_translations: number;
    errors: number;
  };
}
```

### 2. Model Management Component

**File**: `components/model-management.tsx`

**Features**:
- List available models
- Show download status
- Download progress for models
- Model size and requirements
- Delete models

**API Integration**:
```typescript
// GET /local_gpu/models/list
// POST /local_gpu/models/download
interface ModelInfo {
  model_id: string;
  name: string;
  downloaded: boolean;
  size_gb: number;
  local_path?: string;
}
```

### 3. GPU Status Component

**File**: `components/gpu-status.tsx`

**Features**:
- GPU detection status
- Available GPU memory
- GPU requirements check
- Warnings if GPU unavailable

**API Integration**:
```typescript
// GET /local_gpu/gpu/status
interface GPUStatus {
  cuda_available: boolean;
  gpu_count: number;
  gpus: Array<{
    name: string;
    memory_gb: number;
    available_memory_gb: number;
  }>;
}
```

### 4. Progress Tracker Component

**File**: `components/translation-progress.tsx`

**Features**:
- Real-time progress bar
- ETA display
- Statistics (exact matches, fuzzy repairs, new translations)
- Error count
- Cancel button

**Integration**:
- WebSocket or polling for progress updates
- Display statistics from workflow

### 5. Quality Results Viewer

**File**: `components/quality-results.tsx`

**Features**:
- Display quality scores per segment
- Filter by quality threshold
- Show match rates
- Highlight problematic segments
- Export quality report

### 6. Profile Management UI

**File**: `components/profile-management.tsx`

**Features**:
- List profiles
- Create/edit/delete profiles
- Profile settings form:
  - Model selection
  - TQE weights
  - Thresholds
  - Term enforcement policy
- Profile switching

---

## Integration Points

### 1. Flask Blueprint Registration

In the main TMXmatic Flask app (`app.py` or similar):

```python
from local_gpu_translation.api.endpoints import local_gpu_bp

# Register the blueprint
app.register_blueprint(local_gpu_bp, url_prefix='/api/local_gpu')
```

### 2. Operations Panel Update

Update `components/operations-panel.tsx` to include new operation:

```typescript
export type Operation = 
  | 'split_by_language'
  | 'merge_tmx'
  | 'translate_with_gpu'  // NEW
  | 'quality_estimation'  // NEW
  // ... existing operations
```

### 3. Workspace Integration

Update `components/tmx-workspace.tsx` to:
- Show GPU translation option when XLIFF file is loaded
- Display quality scores in segment view
- Show match rates in translation memory matches

---

## API Endpoints Summary

### GPU Status
- `GET /api/local_gpu/gpu/status` - Get GPU status

### Model Management
- `GET /api/local_gpu/models/list` - List models
- `POST /api/local_gpu/models/download` - Download model

### Translation
- `POST /api/local_gpu/translate` - Translate XLIFF
- `GET /api/local_gpu/translate/download?path=<path>` - Download result

---

## UI Flow

### Translation Workflow

1. **User selects XLIFF file** in workspace
2. **Translation panel appears** with options
3. **User selects**:
   - Target language
   - TMX file (optional)
   - TBX file (optional)
   - Profile (optional)
4. **User clicks "Translate"**
5. **Progress tracker shows**:
   - Progress bar
   - ETA
   - Statistics
6. **On completion**:
   - Results displayed
   - Quality scores shown
   - Download button available

### Model Management Flow

1. **User opens model management panel**
2. **System checks** model status
3. **User can**:
   - View available models
   - Download missing models
   - See download progress
   - Delete models

---

## Styling Considerations

- Match existing TMXmatic UI style
- Use existing component library
- Follow existing color scheme
- Maintain responsive design

---

## Error Handling

### UI Error Display
- Show errors in toast notifications
- Display error details in error panel
- Provide retry options where applicable
- Show partial results if available

### Error Scenarios
- GPU not available → Show warning, allow CPU fallback
- Model not downloaded → Prompt to download
- Translation failure → Show error, allow retry
- Partial failure → Show partial results

---

## Testing UI Components

### Unit Tests
- Test component rendering
- Test API integration
- Test error handling
- Test user interactions

### Integration Tests
- Test complete translation workflow
- Test model download flow
- Test error scenarios
- Test progress tracking

---

## Implementation Priority

### Phase 1: Core Functionality
1. Translation panel
2. GPU status display
3. Basic progress tracking

### Phase 2: Enhanced Features
1. Model management UI
2. Quality results viewer
3. Profile management UI

### Phase 3: Polish
1. Advanced progress visualization
2. Quality filtering and sorting
3. Export functionality

---

## Notes

- UI components should be added to existing TMXmatic UI structure
- Follow existing patterns and conventions
- Ensure accessibility (WCAG compliance)
- Support keyboard navigation
- Mobile-responsive design

---

**Status**: ⏳ **PENDING IMPLEMENTATION**  
**Next Steps**: Create UI components following this guide
