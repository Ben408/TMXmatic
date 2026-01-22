# LLM Quality Module - Questions & Clarifications

**Status**: ✅ All Questions Answered  
**Priority**: Ready for Implementation  
**Last Updated**: Answers received, updating implementation plan

---

## High Priority Questions

### 1. Auth/User Management Integration

**Question**: When auth/user management is available, how should profile management integrate?
A user should only ever see their own profiles.

**Context**: 
- Auth and user management are being developed by a different engineer
- This module needs to work both before and after auth is available
- Profile storage location: `{TMXmatic_install_dir}/config/profiles/`

**Specific Sub-questions**:
1. **Profile Ownership**: Should profiles be:
   - **Option A**: User-specific (each user has their own profiles)
   - **Option B**: Organization/shared (profiles shared across team)
   - **Option C**: Hybrid (users can create personal profiles + access org profiles)

2. **User Context**: How should the module access user context?
   - From Flask session?
   - From auth token/JWT?
   - From request headers?
   - **Current assumption**: Module should work without auth initially, gracefully integrate when available

3. **Profile Access Control**: If profiles are shared, should there be:
   - Read-only vs read-write permissions?
   - Profile ownership/creator tracking?
   - Profile visibility (public vs private)?

**Proposed Approach** (needs confirmation):
- **Phase 1 (no auth)**: Single global profiles directory, all profiles accessible
- **Phase 2 (with auth)**: 
  - User-specific profiles in `{install_dir}/config/profiles/{user_id}/`
  - Organization profiles in `{install_dir}/config/profiles/org_{org_id}/`
  - Fallback to global profiles if user/org not specified

**✅ ANSWERED**: 
- **Option A**: User-specific profiles only
- Users only see their own profiles + global profile (if any)
- Module works without auth initially, gracefully integrates when available
- **Storage**: `{install_dir}/config/profiles/{user_id}/` (with auth), `{install_dir}/config/profiles/` (without auth)

---

### 2. LLM Prompt Engineering for Fuzzy Match Repair

**Question**: What specific prompt format should be used for "repair fuzzy match" task?

**Context**:
- High fuzzy matches (≥threshold) need LLM to repair/improve the existing fuzzy TMX translation
- LLM should fix errors, improve fluency, align terminology, correct grammar

**Specific Sub-questions**:
1. **Prompt Structure**: Should we use:
   - **Option A**: Simple instruction format
     ```
     "The following translation is a fuzzy match (85% similarity) for the source text. 
     Please repair and improve it to better match the source while maintaining meaning.
     
     Source: {source_text}
     Fuzzy Translation: {fuzzy_translation}
     
     Please provide an improved translation."
     ```
   
   - **Option B**: Detailed repair instructions
     ```
     "You are a translation quality expert. The following translation is a fuzzy match 
     that needs improvement.
     
     Source: {source_text}
     Current Translation: {fuzzy_translation}
     Similarity: {similarity}%
     
     Please:
     1. Fix any grammatical errors
     2. Correct terminology to match approved terms
     3. Improve fluency while maintaining meaning
     4. Ensure alignment with source structure
     
     Provide the repaired translation."
     ```
   
   - **Option C**: Template-based with term injection
     ```
     "Repair and improve this fuzzy translation (similarity: {similarity}%).
     
     Source: {source_text}
     Current Translation: {fuzzy_translation}
     
     Approved Terms (use these exact terms when applicable):
     {term_list}
     
     Provide improved translation."
     ```

2. **Term Injection**: Should approved terms be included in fuzzy match repair prompts?
   - If yes, format same as new translation prompts?
   - Or different format since we're repairing existing translation?

3. **Context Preservation**: Should we preserve:
   - Original fuzzy match similarity score in the prompt?
   - Specific issues identified (if any)?
   - Source segment metadata?

**Proposed Approach** (needs confirmation):
- Use **Option C** (template-based with term injection) for consistency
- Include approved terms if available (same format as new translation)
- Include similarity score for context
- Generate 3-5 repaired candidate variations

**✅ ANSWERED**: 
- **Format**: Use detailed repair instructions (Option B equivalent) with two versions:
  - Version 1: With approved terms included
  - Version 2: Without approved terms
- **Term Injection**: Include approved terms in both fuzzy repair AND new segment generation if termbase available
- **Tag Preservation**: Tags in source content must be placed correctly and in correct order in target segment
- **Prompt Externalization**: Prompts should be externalized (INI/config file or similar) for easy editing and maintenance
  - Reference: `C:\Users\bjcor\Desktop\Sage Local\Process_Variants` for examples
  - Prompts should be editable via UI by users
- **Format Example** (with terms):
  ```
  "You are a translation quality expert. The following translation is a fuzzy match that needs improvement.
  
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
  
  Provide the repaired translation."
  ```

---

### 3. Fuzzy Match Repair vs New Translation Strategy

**Question**: For high fuzzy matches, should we generate multiple candidates that include repaired versions AND new translations, or only repaired versions?

**Context**:
- High fuzzy matches (≥threshold) get sent to LLM for repair
- Question is whether to also generate completely new translations for comparison

**Specific Sub-questions**:
1. **Candidate Mix**: Should we generate:
   - **Option A**: Only repaired versions of fuzzy match (3-5 candidates)
   - **Option B**: Mix of repaired versions + new translations (e.g., 3 repaired + 2 new)
   - **Option C**: Separate repair task, then generate new translations, then TQE scores both sets

2. **TQE Scoring**: Should we:
   - Score repaired candidates against the fuzzy match (reference)?
   - Score repaired candidates against source only?
   - Score both repaired and new translations together?

3. **Selection Logic**: If we have both repaired and new candidates:
   - How should TQE choose the best?
   - Should repaired candidates get priority boost (they're closer to human translation)?
   - Or pure score-based selection?

**Proposed Approach** (needs confirmation):
- **Option A**: Generate only repaired versions (3-5 candidates)
- Score repaired candidates against source (primary) and fuzzy match (secondary reference)
- Rationale: Fuzzy match exists because it's close enough; repair is more efficient than starting from scratch
- If repair quality is poor, flag for human review

**✅ ANSWERED**: 
- **Use Proposed Approach (Option A)**: Generate only repaired versions (3-5 candidates)
- Score repaired candidates against source (primary) and fuzzy match (secondary reference)
- Rationale: Fuzzy match exists because it's close enough; repair is more efficient than starting from scratch
- If repair quality is poor, flag for human review

---

### 4. Dynamic Dependencies Integration

**Question**: How should this module's dependencies integrate with the existing dynamic dependency system?

**Context**:
- Dynamic dependency installation is already implemented
- This module needs: torch, transformers, sentence-transformers, bert-score, lxml, rapidfuzz, huggingface-hub, uqlm (from GitHub)

**Specific Sub-questions**:
1. **Dependency Registration**: Should we:
   - Register all dependencies with dynamic dependency system?
   - Or handle GPU-related dependencies separately?
   - Which dependencies should be "optional" (only if GPU available)?

2. **Model Downloads**: Should model downloads (translategemma, COMET) use the dynamic dependency pattern?
   - Or separate model manager?
   - How to handle large model files (20GB+) vs smaller dependencies?

3. **Installation Detection**: How should we detect if dependencies are available?
   - Check at module import time?
   - Check at runtime before use?
   - Graceful fallback if dependencies missing?

4. **GPU Dependencies**: Should torch (CUDA) be:
   - Required dependency (fail if not available)?
   - Optional with graceful CPU fallback?
   - Detected and installed only if GPU available?

**Proposed Approach** (needs confirmation):
- Register all dependencies with dynamic dependency system
- Mark GPU dependencies (torch with CUDA) as optional/conditional
- Model downloads handled separately by model_manager.py (not via dependency system)
- Check dependencies at module import, fail gracefully with clear error messages

**✅ ANSWERED**: 
- Register all dependencies with dynamic dependency system
- Mark GPU dependencies (torch with CUDA) as optional/conditional
- Model downloads handled separately by model_manager.py (not via dependency system)
- Check dependencies at module import, fail gracefully with clear error messages

---

## Medium Priority Questions

### 5. Okapi Integration Relationship

**Question**: Should this module be aware of Okapi processing that might happen before/after?

**Context**:
- Okapi integration is being developed separately
- Okapi handles format conversion, segmentation, etc.
- Files might be processed by Okapi before reaching this module

**Specific Sub-questions**:
1. **File Flow**: Should we:
   - Expect files to come from Okapi preprocessing?
   - Handle files directly without Okapi dependency?
   - Support both workflows?

2. **Format Considerations**: Any special considerations when:
   - Okapi processes XLIFF first (segmentation, formatting)
   - We then add quality metadata
   - File goes back through Okapi

3. **Metadata Preservation**: Will Okapi preserve our quality metadata?
   - Or do we need to re-apply metadata after Okapi processing?
   - Any namespace conflicts?

**Proposed Approach** (needs confirmation):
- Module should work independently (no Okapi dependency)
- Files can come from Okapi or directly from user
- Use standard XLIFF metadata (not custom props) to maximize compatibility
- Document recommended workflow if Okapi is in the pipeline

**✅ ANSWERED**: 
- Module should work independently (no Okapi dependency)
- Files can come from Okapi or directly from user
- Use standard XLIFF metadata (not custom props) to maximize compatibility
- Document recommended workflow if Okapi is in the pipeline

---

### 6. Multi-Agent System Future Integration

**Question**: Should we design TQE scoring to be reusable by multi-agent system?

**Context**:
- Multi-agent system uses serverless LLMs (RunPod/HF)
- This module uses local GPU LLMs
- Both might benefit from shared TQE scoring

**Specific Sub-questions**:
1. **TQE Reusability**: Should TQE scoring engine:
   - Be a standalone module that both systems can use?
   - Be tightly coupled to local GPU module?
   - Have adapter/interface for multi-agent system?

2. **Shared Components**: What should be shared?
   - TQE scoring algorithms?
   - Terminology validation?
   - Metadata writing?
   - Configuration profiles?

3. **API Design**: Should TQE expose:
   - Simple function calls?
   - Flask endpoints?
   - Both?

**Proposed Approach** (needs confirmation):
- Design TQE as relatively independent module
- Keep interfaces clean for potential reuse
- Don't tightly couple to local GPU implementation
- Multi-agent system can call TQE functions directly or via adapter
- Future integration can happen without major refactoring

**✅ ANSWERED**: 
- **IMPORTANT CONSIDERATION**: Multi-agent system also requires GPU
- **Question**: Should multi-agent architecture be included in this new GPU module?
  - Many shared needs: model management, GPU management, etc.
  - Options:
    1. Build shared functionality that multi-agent reuses
    2. Replicate functions for multi-agent (not ideal)
    3. Integrate multi-agent goals into current GPU module
- **Proposed Approach**: Design TQE as relatively independent module with clean interfaces
- Keep interfaces clean for potential reuse
- Don't tightly couple to local GPU implementation
- Multi-agent system can call TQE functions directly or via adapter
- Future integration can happen without major refactoring
- **Decision Pending**: Need to decide if multi-agent should be integrated now or later

---

### 7. Workspace File Management

**Question**: How should processed files with quality metadata be handled in the existing workspace?

**Context**:
- Existing workspace pattern in `tmx-workspace.tsx`
- Files have `status`, `operations`, `processedData`, etc.
- Need to integrate quality metrics display

**Specific Sub-questions**:
1. **File Status**: Should processed files show:
   - Quality score summary in file list?
   - Quality indicator badge/icon?
   - Status like "translated (avg score: 87/100)"?

2. **Metadata Storage**: Where should quality metadata be stored?
   - In the processed file itself (XLIFF)?
   - In workspace file object as additional property?
   - Both?

3. **Quality Details View**: Should we:
   - Extend existing stats dialog pattern (`xliff-stats-dialog.tsx`)?
   - Create new quality metrics dialog?
   - Show segment-level details inline?

4. **Filtering/Sorting**: Should users be able to:
   - Filter files by quality score?
   - Sort by quality metrics?
   - Show only files needing review?

**Proposed Approach** (needs confirmation):
- Store metadata in XLIFF file (primary source)
- Add quality summary to workspace file object for quick access
- Extend `xliff-stats-dialog.tsx` pattern for quality metrics display
- Add quality score badge/indicator in file list
- Future: Add filtering/sorting by quality (Phase 2 enhancement)

**✅ ANSWERED**: 
- Store metadata in XLIFF file (primary source)
- Add quality summary to workspace file object for quick access
- Extend `xliff-stats-dialog.tsx` pattern for quality metrics display
- Add quality score badge/indicator in file list
- Future: Add filtering/sorting by quality (Phase 2 enhancement)

---

## Low Priority Questions

### 8. Model Caching Strategy

**Question**: Should model downloads be shared across users in multi-user scenarios, or per-user?

**Context**:
- Models can be very large (12-24GB for translategemma)
- Multiple users on same system might share GPU resources

**Specific Sub-questions**:
1. **Storage Location**: Models stored in:
   - Shared location: `{install_dir}/models/` (all users)
   - Per-user: `{install_dir}/models/{user_id}/`
   - Hybrid: Shared models, user-specific configs

2. **Access Control**: If shared:
   - Any access control needed?
   - Who can delete models?
   - Disk quota considerations?

3. **Multi-GPU Scenarios**: If multiple users want to use same model:
   - Concurrent access OK?
   - Model loading/unloading coordination?
   - GPU resource sharing?

**Proposed Approach** (needs confirmation):
- **Phase 1**: Shared models in `{install_dir}/models/` (simpler)
- **Phase 2**: Hybrid approach if multi-user support needed:
  - Shared model files (hard links to save space)
  - User-specific model configurations
  - GPU resource queue/coordination if needed

**✅ ANSWERED**: 
- **Phase 1**: Shared models in `{install_dir}/models/` (all users can access)
- Downloaded models are available to all users
- Future: Consider user-specific configs if needed, but models remain shared

---

### 9. Progress Tracking Implementation Details

**Question**: Should we use existing progress tracking pattern or create new SSE endpoints?

**Context**:
- Existing workspace has progress tracking
- Translation jobs can be long-running (minutes to hours)
- Need real-time progress updates

**Specific Sub-questions**:
1. **Progress Endpoint**: Should we:
   - Use existing progress tracking infrastructure?
   - Create new `/api/llm_translate/status/<job_id>` endpoint?
   - Reuse existing pattern with new job types?

2. **Update Frequency**: What granularity?
   - Per segment processed?
   - Every N segments (e.g., 10)?
   - Time-based (e.g., every 5 seconds)?
   - User-configurable?

3. **Progress Data**: What information to include?
   - Segments processed / total
   - Estimated time remaining
   - Current phase (matching, translation, scoring)
   - GPU memory usage
   - Errors/warnings count

4. **SSE vs Polling**: Implementation preference:
   - Server-Sent Events (SSE) for real-time push
   - Polling with configurable interval
   - Both (SSE primary, polling fallback)

**Proposed Approach** (needs confirmation):
- Create new job-based progress tracking system
- Use SSE for real-time updates (if supported by existing infrastructure)
- Fallback to polling if SSE not available
- Update every 10 segments or 5 seconds (whichever comes first)
- Include: progress %, current phase, ETA, memory usage

**✅ ANSWERED**: 
- **Reuse existing pattern** with new job types
- New job types are added if GPU module is installed (replacing or updating base .tsx file)
- **Use SSE** for real-time updates (if supported by existing infrastructure)
- **Update frequency**: Every 100 segments or 15 seconds (whichever comes first)
- **Include**: progress %, current phase, ETA, memory usage

---

## Implementation Assumptions (Need Confirmation)

### Assumption 1: LLM Model Loading Strategy
**Assumption**: Load translategemma-12b-it on-demand when translation operation starts, unload after completion (or keep in memory if another job queued).

**✅ ANSWERED**: 
- **Keep model loaded** for better performance
- Model stays in memory between translation jobs
- Consider memory management for long idle periods if needed

### Assumption 2: Error Recovery Strategy
**Assumption**: Single segment failures log and continue; systematic failures (5 consecutive) fail fast with partial results saved.

**✅ ANSWERED**: 
- Single segment failures: Log and continue
- Systematic failures: 5 consecutive failures → fail fast with partial results saved
- Thresholds are acceptable as-is (can be made configurable in future if needed)

### Assumption 3: Batch Processing Strategy
**Assumption**: Process in chunks of 100 segments, save partial results every 50 segments.

**✅ ANSWERED**: 
- **Start with**: 100 segment chunks, save partial results every 50 segments
- **Rationale**: TUs can range from single word to entire paragraphs
- Content may be UI strings or technical/marketing documents
- Monitor for problems before adding memory dependencies or adaptive adjustments
- Keep it simple initially, optimize based on real-world usage

---

## Summary of Decisions

| Priority | Question | Status | Answer Summary |
|----------|----------|--------|----------------|
| High | 1. Auth/User Management Integration | ✅ Answered | Option A: User-specific profiles only |
| High | 2. LLM Prompt Engineering | ✅ Answered | Externalized prompts, two versions (with/without terms) |
| High | 3. Fuzzy Match Repair Strategy | ✅ Answered | Option A: Only repaired versions |
| High | 4. Dynamic Dependencies Integration | ✅ Answered | Register with dynamic dependency system |
| Medium | 5. Okapi Integration Relationship | ✅ Answered | Independent operation, no dependency |
| Medium | 6. Multi-Agent System Integration | ⚠️ Needs Decision | **CRITICAL**: Should multi-agent be integrated into GPU module? |
| Medium | 7. Workspace File Management | ✅ Answered | Extend existing patterns |
| Low | 8. Model Caching Strategy | ✅ Answered | Shared models, all users access |
| Low | 9. Progress Tracking Details | ✅ Answered | Reuse existing pattern, SSE, 100 segments/15s |

**Total Questions**: 9 main questions - 8 answered, 1 needs architectural decision  
**Assumptions**: All 3 confirmed

---

## Next Steps

1. **Review this document** and provide answers to all questions
2. **Confirm assumptions** or provide alternatives
3. **Update implementation plan** with confirmed decisions
4. **Begin implementation** once all clarifications are complete

---

**Note**: Some questions may have dependencies (e.g., auth integration affects profile management). Please indicate if any answers depend on work-in-progress systems and we can proceed with reasonable defaults that can be updated later.
