# Implementation Plan Updates - Based on Clarifications

**Status**: Ready to Update Main Plan  
**Date**: All clarifications received

---

## Summary of Updates Needed

All questions have been answered except one critical architectural decision about multi-agent integration. This document summarizes the updates that need to be made to the main implementation plan.

---

## Key Updates to Apply

### 1. Prompt Externalization System

**New Requirement**: Prompts must be externalized for easy editing and maintenance.

**Implementation**:
- Store prompts in config files (INI format, following Sage Local pattern)
- Location: `{install_dir}/config/prompts/prompt_templates.ini` (or similar)
- Sections in config:
  - `[fuzzy_repair_with_terms]` - Prompt for fuzzy repair with approved terms
  - `[fuzzy_repair_without_terms]` - Prompt for fuzzy repair without terms
  - `[new_translation_with_terms]` - Prompt for new translation with terms
  - `[new_translation_without_terms]` - Prompt for new translation without terms
- UI: Allow users to edit prompts via UI (text editor interface)
- Default prompts included in module, users can customize

**Reference**: `C:\Users\bjcor\Desktop\Sage Local\Process_Variants\config.ini`

**Update Phase 1.2** to include prompt template management.

---

### 2. Profile Management Updates

**Confirmed**: 
- User-specific profiles only (Option A)
- Users see their own profiles + global profile
- Works without auth initially, integrates when available
- Storage: `{install_dir}/config/profiles/{user_id}/` (with auth) or `{install_dir}/config/profiles/` (without auth)

**Update Phase 4.1** to reflect user-specific profile structure.

---

### 3. LLM Model Loading Strategy

**Confirmed**: 
- **Keep model loaded** for better performance
- Model stays in memory between translation jobs
- No on-demand loading/unloading

**Update Phase 1.1** model manager to:
- Load model on first translation operation
- Keep model in memory
- Add memory management for long idle periods (optional)

---

### 4. Progress Tracking Specifications

**Confirmed**:
- Reuse existing pattern with new job types
- SSE for real-time updates (if supported)
- **Update frequency**: Every 100 segments or 15 seconds (whichever comes first)
- Include: progress %, current phase, ETA, memory usage
- New job types update/replace base .tsx file when GPU module installed

**Update Phase 5.2** and Phase 6.1 with exact specifications.

---

### 5. Prompt Format Specifications

**Confirmed**:
- Use detailed repair instructions format
- Two versions: with terms and without terms
- Include tag preservation instructions: "Preserve all tags from source in correct order and position"
- Approved terms included in both fuzzy repair AND new translation if available

**Example prompt structure** (to be externalized):
```
[prompt_templates]
fuzzy_repair_with_terms = You are a translation quality expert. The following translation is a fuzzy match that needs improvement.

Source: {source_text}
Current Translation: {fuzzy_translation}
Similarity: {similarity}%

Approved Terms (use these exact terms when applicable):
{term_list}

Please:
1. Fix any grammatical errors
2. Correct terminology to match approved terms
3. Improve fluency while maintaining meaning
4. Ensure alignment with source structure
5. Preserve all tags from source in correct order and position

Provide the repaired translation.
```

**Update Phase 1.2** to include prompt template system.

---

### 6. Workspace Integration Details

**Confirmed**:
- Extend existing patterns from `tmx-workspace.tsx`
- Store metadata in XLIFF (primary)
- Add quality summary to workspace file object
- Extend `xliff-stats-dialog.tsx` for quality metrics
- Add quality badge/indicator in file list

**Update Phase 6.1** with specific implementation details.

---

### 7. Model Storage

**Confirmed**:
- Shared models: `{install_dir}/models/` (all users)
- Downloaded models available to all users
- No per-user model storage needed initially

**Update Phase 1.1** model manager specifications.

---

### 8. Batch Processing Details

**Confirmed**:
- Start with: 100 segment chunks
- Save partial results every 50 segments
- Monitor for problems before adding memory dependencies
- TUs can range from single word to entire paragraphs
- Content may be UI strings or technical/marketing documents

**Update Phase 1.4** workflow manager with chunking details.

---

## Remaining Decision

### Multi-Agent Integration Question

**Status**: ⚠️ **NEEDS DECISION**

See `MULTI_AGENT_INTEGRATION_DECISION.md` for detailed analysis.

**Question**: Should multi-agent system architecture be integrated into this GPU module?

**Options**:
- A: Separate modules (current plan)
- B: Shared infrastructure, separate modules (recommended)
- C: Unified module with multi-agent support
- D: Build shared infrastructure first

**Recommended**: Option B - Shared infrastructure layer

**Impact**: This decision affects:
- Module structure and organization
- Whether to build shared/common module now
- Architecture of model/GPU management
- Timeline and phases

---

## Next Steps

1. **Review** `MULTI_AGENT_INTEGRATION_DECISION.md`
2. **Make decision** on multi-agent integration approach
3. **Update** `IMPLEMENTATION_PLAN.md` with all confirmed answers
4. **Finalize** architecture based on multi-agent decision
5. **Begin implementation** Phase 1

---

## Files Updated

- ✅ `CLARIFICATIONS_AND_QUESTIONS.md` - All answers recorded
- ✅ `MULTI_AGENT_INTEGRATION_DECISION.md` - Decision document created
- ⏳ `IMPLEMENTATION_PLAN.md` - Needs updating with all confirmed decisions
