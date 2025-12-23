# Auto-Detection Verification Report

## Summary
This report verifies whether auto-detection is actually working for:
1. Document Type Auto-Detection
2. Preprocessing Playbook Auto-Routing
3. Chunking Configuration Auto-Detection

---

## 1. Document Type Auto-Detection

### Current Implementation
**Location**: `ui/app/app/products/new/page.tsx`

**Flow**:
- User selects "Auto-detect" for document type (line 271)
- When document type is "auto", user can manually select playbook via `PlaybookSelector` (lines 286-292)
- If playbook is not selected manually, it will be `undefined` and auto-routed during pipeline

**Code**:
```typescript
// Line 133-135
const finalPlaybookId = documentType !== 'auto' 
  ? getPlaybookFromDocumentType(documentType)  // Maps to specific playbook
  : playbookId  // Can be undefined, will be auto-routed
```

**Status**: ✅ **WORKING CORRECTLY**
- When document type is NOT "auto": Maps to specific playbook (e.g., "scanned" → "SCANNED")
- When document type IS "auto": Playbook can be undefined, triggering auto-routing during pipeline

---

## 2. Preprocessing Playbook Auto-Routing

### Current Implementation
**Location**: `backend/src/primedata/ingestion_pipeline/aird_stages/preprocess.py`

**Flow**:
1. PreprocessStage receives `playbook_id` from context (line 120)
2. If `playbook_id` is None/undefined, it calls `route_playbook()` (lines 212-215)
3. `route_playbook()` analyzes sample text and filename for keywords
4. Returns playbook_id and reason

**Code**:
```python
# Line 212-215 in preprocess.py
if not playbook_id:
    chosen_id, reason = route_playbook(sample_text=raw_text[:1000], filename=file_stem)
    playbook_id = chosen_id
    self.logger.info(f"Auto-routed to playbook {playbook_id} ({reason})")
```

**Auto-Routing Logic** (`backend/src/primedata/ingestion_pipeline/aird_stages/playbooks/router.py`):
- Checks for OCR/scanned keywords: "scanned", "ocr", "image", "tesseract" → routes to "SCANNED"
- Checks for regulatory keywords: "label", "regulatory", "prescribing information", "safety", "fda", "ema" → routes to "REGULATORY"
- Default: Routes to "TECH"

**Status**: ✅ **WORKING CORRECTLY**
- Auto-routing happens when playbook_id is None
- Uses keyword matching on sample text (first 1000 chars) and filename
- Saves playbook_id to product after preprocessing (fixed in recent update)

---

## 3. Chunking Configuration Auto-Detection

### Current Implementation
**Location**: `backend/src/primedata/ingestion_pipeline/aird_stages/preprocess.py`

**Flow**:
1. Product is created with `chunking_config.mode = "auto"` (UI line 148)
2. Auto settings contain defaults: `content_type: 'general'`, `model_optimized: true`, `confidence_threshold: 0.7`
3. During preprocessing, when mode is "auto", it uses **playbook defaults** (lines 362-367)

**Code**:
```python
# Line 362-367 in preprocess.py
elif chunking_config and chunking_config.get("mode") == "auto":
    # Use playbook settings but respect product content_type recommendations if available
    max_tokens = int(playbook_chunking.get("max_tokens", 900))
    overlap_sents = int(playbook_chunking.get("overlap_sentences", 2))
    hard_overlap = int(playbook_chunking.get("hard_overlap_chars", 300))
    strategy = (playbook_chunking.get("strategy", "sentence") or "sentence").lower()
```

**Content Analyzer Exists** (`backend/src/primedata/analysis/content_analyzer.py`):
- `ContentAnalyzer.analyze_content()` can detect content type and recommend optimal chunking
- Detects: CODE, DOCUMENTATION, GENERAL, LEGAL, ACADEMIC, TECHNICAL, CONVERSATION
- Provides optimal chunk_size, chunk_overlap, strategy based on content analysis
- **BUT**: This is NOT being used in the preprocessing pipeline

**Status**: ❌ **NOT FULLY WORKING**
- When mode is "auto", it uses **playbook defaults**, not content analysis
- ContentAnalyzer exists but is **not integrated** into the preprocessing pipeline
- The UI says "Auto (Recommended)" which implies intelligent analysis, but it's just using playbook defaults
- There's a separate API endpoint `/auto-configure-chunking` that uses ContentAnalyzer, but it's not called automatically during pipeline execution

---

## Issues Found

### Issue 1: Chunking Auto-Mode Doesn't Actually Analyze Content
**Problem**: 
- When chunking mode is "auto", it should analyze content to determine optimal settings
- Currently, it just uses playbook defaults
- ContentAnalyzer exists but is not integrated into the pipeline

**Expected Behavior**:
- When mode is "auto", analyze sample content from raw files
- Use ContentAnalyzer to detect content type and recommend settings
- Apply recommended settings or use playbook defaults as fallback

**Current Behavior**:
- Uses playbook chunking defaults directly
- No content analysis happens

### Issue 2: Auto Settings Are Not Used
**Problem**:
- Product is created with `auto_settings: { content_type: 'general', ... }`
- But these settings are **ignored** during preprocessing
- Only playbook defaults are used

**Code Evidence**:
```python
# Line 362-367: Uses playbook defaults, ignores auto_settings.content_type
elif chunking_config and chunking_config.get("mode") == "auto":
    max_tokens = int(playbook_chunking.get("max_tokens", 900))  # Playbook default
    # auto_settings.content_type is never checked or used
```

---

## Recommendations

### Fix 1: Integrate ContentAnalyzer into Preprocessing
When `chunking_config.mode == "auto"`:
1. Analyze sample content from raw files using ContentAnalyzer
2. Get recommended chunking settings
3. Use recommended settings, with playbook defaults as fallback
4. Log the analysis results

### Fix 2: Use Auto Settings When Provided
If `auto_settings.content_type` is provided and not "general":
1. Use it to guide chunking configuration
2. Override playbook defaults with analyzed recommendations

### Fix 3: Make Auto-Detection More Transparent
- Log when auto-detection happens
- Show detected content type and confidence in UI
- Display which playbook was auto-selected and why

---

## Verification Results

| Feature | Status | Notes |
|---------|--------|-------|
| Document Type Auto-Detection | ✅ Working | Correctly allows manual selection or auto-routing |
| Playbook Auto-Routing | ✅ Working | Uses keyword matching on text/filename |
| Chunking Auto-Detection | ❌ Not Working | Uses playbook defaults, doesn't analyze content |

---

## Conclusion

**Document Type and Playbook auto-detection are working correctly.**

**Chunking auto-detection is NOT working as expected:**
- It's labeled as "Auto (Recommended)" in the UI
- But it only uses playbook defaults, not content analysis
- ContentAnalyzer exists but is not integrated into the pipeline
- Auto settings provided during product creation are ignored

The system needs to integrate ContentAnalyzer into the preprocessing pipeline to truly provide "auto" chunking configuration based on content analysis.

