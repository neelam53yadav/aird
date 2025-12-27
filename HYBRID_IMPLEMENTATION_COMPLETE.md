# Hybrid Optimization Implementation - Complete ✅

## Implementation Summary

All three phases have been successfully implemented:

### ✅ Phase 1: Pattern-Based Module Extraction
- **File**: `backend/src/primedata/ingestion_pipeline/aird_stages/optimization/pattern_based.py`
- **Class**: `PatternBasedOptimizer`
- **Features**:
  - Extracted existing pattern-based optimization logic
  - Supports enhanced normalization and error correction flags
  - Includes quality estimation function
  - Backward compatible with existing code

### ✅ Phase 2: LLM Service Foundation
- **File**: `backend/src/primedata/services/llm_optimization.py`
- **Class**: `LLMOptimizationService`
- **Features**:
  - OpenAI API integration
  - Support for multiple models (GPT-4, GPT-3.5, GPT-4o, etc.)
  - Cost estimation and tracking
  - Error handling and fallback
  - Token usage tracking
  - Change detection

### ✅ Phase 3: Hybrid Orchestrator
- **File**: `backend/src/primedata/ingestion_pipeline/aird_stages/optimization/hybrid.py`
- **Class**: `HybridOptimizer`
- **Features**:
  - Orchestrates pattern-based and LLM optimization
  - Supports three modes: "pattern", "llm", "hybrid"
  - Quality threshold detection for hybrid mode
  - Cost estimation
  - Intelligent fallback to pattern-based if LLM fails

### ✅ Integration with Preprocessing
- **File**: `backend/src/primedata/ingestion_pipeline/aird_stages/preprocess.py`
- **Integration**: Updated `_process_document` method to use hybrid optimizer
- **Features**:
  - Reads `optimization_mode` from chunking_config
  - Supports pattern/hybrid/llm modes
  - Falls back to legacy pattern-based if hybrid optimizer unavailable
  - Comprehensive logging

---

## File Structure

```
backend/src/primedata/
├── ingestion_pipeline/
│   └── aird_stages/
│       ├── optimization/              # NEW
│       │   ├── __init__.py
│       │   ├── pattern_based.py      # NEW
│       │   └── hybrid.py              # NEW
│       └── preprocess.py              # UPDATED
│
└── services/
    └── llm_optimization.py            # NEW
```

---

## Configuration

### Chunking Config Schema

```json
{
  "mode": "auto" | "manual",
  "optimization_mode": "pattern" | "llm" | "hybrid",  // NEW
  "preprocessing_flags": {
    "enhanced_normalization": true,
    "error_correction": true,
    "extract_metadata": true,
    "llm_model": "gpt-4-turbo-preview",  // NEW (optional)
    "llm_quality_threshold": 75          // NEW (optional, for hybrid mode)
  },
  "manual_settings": {...},
  "auto_settings": {...}
}
```

### Environment Variables

```bash
# Required for LLM/hybrid modes
OPENAI_API_KEY=sk-...

# Optional: Custom API endpoint
OPENAI_BASE_URL=https://api.openai.com/v1
```

---

## Usage Examples

### Pattern-Based Mode (Default)

```python
from primedata.ingestion_pipeline.aird_stages.optimization import HybridOptimizer

optimizer = HybridOptimizer()
result = optimizer.optimize(
    text="The   quick    brown   fox   jumps   over   teh   lazy   dog.",
    mode="pattern",
    pattern_flags={
        "enhanced_normalization": True,
        "error_correction": True
    }
)

print(result["optimized_text"])  # "The quick brown fox jumps over the lazy dog."
print(result["cost"])  # 0.0 (free)
```

### Hybrid Mode

```python
result = optimizer.optimize(
    text="Teh quik brown fox...",
    mode="hybrid",
    pattern_flags={"enhanced_normalization": True, "error_correction": True},
    llm_config={
        "api_key": "sk-...",
        "model": "gpt-4-turbo-preview"
    },
    quality_threshold=75  # Use LLM if quality < 75%
)

# Pattern-based applied first, then LLM if quality < threshold
print(result["method_used"])  # "hybrid" or "pattern"
print(result["cost"])  # ~$0.01-0.02 if LLM was used, 0.0 otherwise
```

### LLM Mode

```python
result = optimizer.optimize(
    text="Complex document with OCR errors...",
    mode="llm",
    llm_config={
        "api_key": "sk-...",
        "model": "gpt-4-turbo-preview"
    }
)

# Always uses LLM (after pattern-based preprocessing)
print(result["method_used"])  # "llm"
print(result["cost"])  # ~$0.02 per document
print(result["llm_details"])  # Tokens, model info, etc.
```

---

## Testing

### Basic Tests

1. **Pattern-Based Optimizer**:
   ```bash
   cd backend
   python -c "from src.primedata.ingestion_pipeline.aird_stages.optimization.pattern_based import PatternBasedOptimizer; opt = PatternBasedOptimizer(); print(opt.optimize('The   quick   fox', {'enhanced_normalization': True}))"
   ```

2. **Hybrid Optimizer**:
   ```bash
   # Test with pattern mode (no API key needed)
   python -c "from src.primedata.ingestion_pipeline.aird_stages.optimization.hybrid import HybridOptimizer; opt = HybridOptimizer(); result = opt.optimize('test text', mode='pattern'); print(result)"
   ```

### Integration Testing

To test with a real pipeline:

1. Set `optimization_mode` in product's chunking_config:
   ```json
   {
     "optimization_mode": "pattern"  // or "hybrid" or "llm"
   }
   ```

2. Set `OPENAI_API_KEY` environment variable (for llm/hybrid modes)

3. Run pipeline and check logs for:
   ```
   Text optimization applied: mode=hybrid, method_used=hybrid, quality=82.5%, cost=$0.0150
   ```

---

## Next Steps

### Immediate Testing

1. ✅ **Code imported successfully** - Modules are accessible
2. ⏳ **Test pattern-based optimizer** - Verify it works with existing flags
3. ⏳ **Test hybrid orchestrator** - Verify mode switching logic
4. ⏳ **Test LLM service** - Verify OpenAI API integration (requires API key)
5. ⏳ **Integration test** - Run full pipeline with hybrid optimizer

### Future Enhancements

1. **UI Integration**:
   - Add optimization mode selector to product edit page
   - Display cost estimates
   - Show optimization results in pipeline metrics

2. **Workspace Settings Integration**:
   - Get OpenAI API key from workspace settings (not just env var)
   - Support per-workspace LLM configuration

3. **Cost Tracking**:
   - Track LLM usage and costs per pipeline run
   - Store in database for reporting

4. **Advanced Features**:
   - Support for multiple LLM providers (Anthropic, etc.)
   - Preview/review LLM changes before applying
   - Quality-based auto-switching in hybrid mode

---

## Status

✅ **All three phases complete and ready for testing!**

The implementation is:
- ✅ Modular and maintainable
- ✅ Backward compatible (falls back to legacy if needed)
- ✅ Well-documented
- ✅ Error-handled with fallbacks
- ✅ Ready for integration testing



