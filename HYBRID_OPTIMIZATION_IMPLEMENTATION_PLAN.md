# Hybrid Optimization Implementation Plan

## Overview

Implement a hybrid optimization approach that combines:
1. **Pattern-Based Optimization** (Default, Fast, Free) - Current implementation
2. **LLM-Based Enhancement** (Optional, Intelligent, Paid) - New feature
3. **Smart Hybrid Mode** (Auto-select based on quality) - New feature

---

## Implementation Phases

### Phase 1: Foundation & Configuration ✅ (Current)
- Pattern-based optimization (already implemented)
- Configuration flags system (already implemented)
- Preprocessing flags for optimization modes

### Phase 2: LLM Service Integration 🆕
- LLM API service wrapper
- Support for OpenAI, Anthropic Claude, etc.
- Error handling and retries
- Cost tracking and estimation

### Phase 3: User Interface 🆕
- Optimization mode selector in UI
- Cost estimation display
- Preview/review LLM changes
- Quality-based recommendations

### Phase 4: Hybrid Intelligence Logic 🆕
- Quality threshold detection
- Auto-trigger LLM when quality < threshold
- Cost-optimized hybrid decisions
- Fallback mechanisms

---

## Architecture Design

### Backend Structure

```
backend/src/primedata/
├── ingestion_pipeline/
│   └── aird_stages/
│       ├── preprocess.py (existing - pattern-based)
│       └── optimization/
│           ├── __init__.py
│           ├── pattern_based.py (extract existing logic)
│           ├── llm_based.py (new)
│           └── hybrid.py (new - orchestrator)
│
└── services/
    └── llm_optimization.py (new - LLM API client)
```

### Configuration Schema

```python
# chunking_config structure
{
    "mode": "auto" | "manual",
    "optimization_mode": "pattern" | "llm" | "hybrid",  # NEW
    "preprocessing_flags": {
        "enhanced_normalization": true,
        "error_correction": true,
        "extract_metadata": true,
        "llm_enhancement": false,  # NEW
        "llm_model": "gpt-4-turbo-preview",  # NEW
        "llm_quality_threshold": 75,  # NEW - trigger LLM if quality < this
    },
    "manual_settings": {...},
    "auto_settings": {...}
}
```

---

## Implementation Details

### 1. LLM Service (`services/llm_optimization.py`)

```python
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class LLMOptimizationService:
    """Service for LLM-based text optimization."""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        self.api_key = api_key
        self.model = model
        self.cost_per_1k_tokens = 0.01  # Approximate cost
        
    def enhance_text(
        self, 
        text: str, 
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to enhance text quality.
        
        Returns:
            {
                "enhanced_text": str,
                "changes_made": List[str],
                "cost_estimate": float,
                "tokens_used": int
            }
        """
        # Implementation here
        pass
    
    def estimate_cost(self, text_length: int) -> float:
        """Estimate cost for text optimization."""
        # Rough estimate: 1 token ≈ 4 characters
        estimated_tokens = text_length / 4
        # Input + output tokens (assume 2x for output)
        total_tokens = estimated_tokens * 3
        return (total_tokens / 1000) * self.cost_per_1k_tokens
```

### 2. Hybrid Optimization Orchestrator

```python
# optimization/hybrid.py

class HybridOptimizer:
    """Orchestrates pattern-based and LLM-based optimization."""
    
    def optimize(
        self,
        text: str,
        mode: str,  # "pattern" | "llm" | "hybrid"
        pattern_flags: Dict[str, bool],
        llm_config: Optional[Dict[str, Any]] = None,
        quality_threshold: int = 75
    ) -> Dict[str, Any]:
        """
        Optimize text using hybrid approach.
        
        Args:
            text: Input text
            mode: Optimization mode
            pattern_flags: Flags for pattern-based optimization
            llm_config: LLM configuration (API key, model, etc.)
            quality_threshold: Quality score threshold to trigger LLM
        
        Returns:
            {
                "optimized_text": str,
                "method_used": "pattern" | "llm" | "hybrid",
                "quality_score": float,
                "cost": float,
                "changes": List[str]
            }
        """
        result = {
            "optimized_text": text,
            "method_used": "pattern",
            "quality_score": 0.0,
            "cost": 0.0,
            "changes": []
        }
        
        # Step 1: Always apply pattern-based first (fast, free)
        from .pattern_based import PatternBasedOptimizer
        pattern_optimizer = PatternBasedOptimizer()
        
        optimized_text = pattern_optimizer.optimize(text, pattern_flags)
        quality_score = self._estimate_quality(optimized_text)
        
        result["optimized_text"] = optimized_text
        result["quality_score"] = quality_score
        
        # Step 2: Apply LLM enhancement if needed
        if mode == "llm" or (mode == "hybrid" and quality_score < quality_threshold):
            if llm_config:
                from primedata.services.llm_optimization import LLMOptimizationService
                llm_service = LLMOptimizationService(
                    api_key=llm_config.get("api_key"),
                    model=llm_config.get("model", "gpt-4-turbo-preview")
                )
                
                llm_result = llm_service.enhance_text(optimized_text)
                result["optimized_text"] = llm_result["enhanced_text"]
                result["method_used"] = "llm" if mode == "llm" else "hybrid"
                result["cost"] = llm_result.get("cost_estimate", 0.0)
                result["changes"].extend(llm_result.get("changes_made", []))
        
        return result
    
    def _estimate_quality(self, text: str) -> float:
        """Quick quality estimation (heuristic, not full scoring)."""
        # Simple heuristic based on:
        # - Excessive whitespace ratio
        # - Common OCR error patterns
        # - Punctuation quality
        # This is a fast approximation, not full quality scoring
        
        if not text:
            return 0.0
        
        # Check for excessive spaces (corruption indicator)
        space_ratio = text.count(' ') / len(text) if len(text) > 0 else 0
        if space_ratio > 0.3:
            return 40.0  # Likely corrupted
        
        # Check for common OCR errors
        ocr_errors = sum(1 for word in ["teh", "adn", "hte"] if word in text.lower())
        error_ratio = ocr_errors / max(len(text.split()), 1)
        
        # Base score
        base_score = 80.0
        # Deduct for issues
        quality = base_score - (space_ratio * 100) - (error_ratio * 20)
        
        return max(0.0, min(100.0, quality))
```

### 3. Integration with Preprocessing Stage

```python
# In preprocess.py _process_document method

def _process_document(self, ...):
    # ... existing code ...
    
    # Get optimization mode from config
    optimization_mode = chunking_config.get("optimization_mode", "pattern")
    preprocessing_flags = chunking_config.get("preprocessing_flags", {})
    
    # Apply optimization
    if optimization_mode in ["pattern", "llm", "hybrid"]:
        from primedata.ingestion_pipeline.aird_stages.optimization.hybrid import HybridOptimizer
        
        optimizer = HybridOptimizer()
        llm_config = None
        
        if optimization_mode in ["llm", "hybrid"]:
            # Get LLM API key from workspace settings or environment
            llm_config = self._get_llm_config(workspace_id)
        
        optimization_result = optimizer.optimize(
            text=cleaned,
            mode=optimization_mode,
            pattern_flags=preprocessing_flags,
            llm_config=llm_config,
            quality_threshold=preprocessing_flags.get("llm_quality_threshold", 75)
        )
        
        cleaned = optimization_result["optimized_text"]
        
        # Log optimization details
        self.logger.info(
            f"Optimization applied: mode={optimization_mode}, "
            f"method_used={optimization_result['method_used']}, "
            f"quality={optimization_result['quality_score']:.1f}%, "
            f"cost=${optimization_result['cost']:.4f}"
        )
    
    # ... rest of processing ...
```

---

## UI Changes

### Product Edit Page

Add optimization mode selector:

```tsx
// In ui/app/app/products/[id]/edit/page.tsx

<div className="space-y-4">
  <div>
    <label>Optimization Mode</label>
    <select 
      value={formData.optimization_mode || 'pattern'}
      onChange={(e) => handleInputChange('optimization_mode', e.target.value)}
    >
      <option value="pattern">
        Standard (Pattern-Based) - Free, Fast
      </option>
      <option value="hybrid">
        Hybrid (Auto) - Pattern + AI when needed
      </option>
      <option value="llm">
        AI Enhancement (LLM) - Best quality, ~$0.02/doc
      </option>
    </select>
  </div>
  
  {formData.optimization_mode !== 'pattern' && (
    <div className="bg-blue-50 p-4 rounded">
      <p className="text-sm">
        <strong>Estimated Cost:</strong> ~$0.01-0.02 per document
      </p>
      <p className="text-sm mt-2">
        AI enhancement will be applied when quality score is below 75%
        (hybrid mode) or for all documents (LLM mode).
      </p>
    </div>
  )}
</div>
```

### Optimization Settings Panel

```tsx
// New component: OptimizationSettings.tsx

<div className="space-y-6">
  <h3>Text Optimization Settings</h3>
  
  {/* Optimization Mode */}
  <div>
    <label>Optimization Mode</label>
    <RadioGroup value={mode} onChange={setMode}>
      <Radio value="pattern">
        <div>
          <strong>Standard (Pattern-Based)</strong>
          <p>Fast, free optimization. Recommended for most documents.</p>
          <p className="text-xs text-gray-500">
            Handles: spacing, quotes, OCR errors, basic formatting
          </p>
        </div>
      </Radio>
      
      <Radio value="hybrid">
        <div>
          <strong>Hybrid (Auto)</strong>
          <p>Pattern-based first, AI enhancement when quality < 75%</p>
          <p className="text-xs text-gray-500">
            Estimated cost: ~$0.01 per document (only when AI is used)
          </p>
        </div>
      </Radio>
      
      <Radio value="llm">
        <div>
          <strong>AI Enhancement (LLM)</strong>
          <p>Best quality with semantic understanding</p>
          <p className="text-xs text-gray-500">
            Estimated cost: ~$0.02 per document
          </p>
        </div>
      </Radio>
    </RadioGroup>
  </div>
  
  {/* LLM Configuration (if mode is llm or hybrid) */}
  {mode !== 'pattern' && (
    <div className="space-y-4 border-t pt-4">
      <h4>AI Enhancement Settings</h4>
      
      <div>
        <label>LLM Model</label>
        <select value={llmModel} onChange={setLlmModel}>
          <option value="gpt-4-turbo-preview">GPT-4 Turbo (Recommended)</option>
          <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Faster, Cheaper)</option>
          <option value="claude-3-opus">Claude 3 Opus (Best Quality)</option>
        </select>
      </div>
      
      <div>
        <label>Quality Threshold (Hybrid Mode)</label>
        <input 
          type="number" 
          value={qualityThreshold} 
          onChange={setQualityThreshold}
          min={50}
          max={90}
        />
        <p className="text-xs">
          Use AI enhancement when quality score is below this threshold
        </p>
      </div>
      
      <div className="bg-yellow-50 p-3 rounded">
        <p className="text-sm font-semibold">Cost Estimate</p>
        <p className="text-sm">
          For {estimatedDocs} documents: ${estimatedCost.toFixed(2)}
        </p>
      </div>
    </div>
  )}
</div>
```

---

## API Changes

### Product Update Request

```python
# In api/products.py

class ChunkingConfigRequest(BaseModel):
    mode: Optional[str] = None
    optimization_mode: Optional[str] = Field(
        default="pattern",
        description="Optimization mode: 'pattern', 'llm', or 'hybrid'"
    )
    auto_settings: Optional[Dict[str, Any]] = None
    manual_settings: Optional[Dict[str, Any]] = None
    preprocessing_flags: Optional[Dict[str, Any]] = None
```

### LLM Configuration Endpoint

```python
# New endpoint: api/optimization.py

@router.post("/api/v1/products/{product_id}/estimate-optimization-cost")
async def estimate_optimization_cost(
    product_id: UUID,
    optimization_mode: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Estimate cost for LLM-based optimization."""
    product = ensure_product_access(db, request, product_id)
    
    # Get document count
    # Estimate tokens
    # Calculate cost
    # Return estimate
    
    return {
        "estimated_cost": 0.0,
        "documents_count": 0,
        "tokens_estimate": 0
    }
```

---

## Migration Path

### Step 1: Extract Pattern-Based Logic ✅
- Create `optimization/pattern_based.py`
- Move existing optimization functions
- Keep backward compatibility

### Step 2: Implement LLM Service 🆕
- Create `services/llm_optimization.py`
- Support OpenAI API first
- Add error handling and retries
- Implement cost tracking

### Step 3: Create Hybrid Orchestrator 🆕
- Create `optimization/hybrid.py`
- Implement hybrid logic
- Quality threshold detection
- Integration with preprocessing

### Step 4: Update Database Schema 🆕
- Add `optimization_mode` to `chunking_config`
- Add LLM configuration fields
- Migration script

### Step 5: Update UI 🆕
- Add optimization mode selector
- Cost estimation display
- Preview/review functionality

### Step 6: Testing & Rollout 🆕
- Unit tests for each component
- Integration tests
- Gradual rollout (feature flag)

---

## Environment Variables

```bash
# LLM API Keys (optional, can also be in workspace settings)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# LLM Configuration
LLM_OPTIMIZATION_ENABLED=true
LLM_DEFAULT_MODEL=gpt-4-turbo-preview
LLM_DEFAULT_QUALITY_THRESHOLD=75
LLM_COST_TRACKING_ENABLED=true
```

---

## Cost Tracking

Track LLM usage and costs:

```python
# New model: db/models.py

class LLMOptimizationUsage(Base):
    """Track LLM optimization usage and costs."""
    __tablename__ = "llm_optimization_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    pipeline_run_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_runs.id"))
    
    optimization_mode = Column(String(20))  # "llm" or "hybrid"
    documents_processed = Column(Integer)
    tokens_used = Column(Integer)
    cost_usd = Column(Numeric(10, 4))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

## Success Metrics

Track:
- Cost per document for LLM optimization
- Quality score improvements
- User adoption of LLM vs pattern-based
- Processing time differences
- Error rates (LLM vs pattern)

---

## Next Steps

1. ✅ **Review this plan**
2. 🆕 **Implement LLM service** (Phase 2)
3. 🆕 **Create hybrid orchestrator** (Phase 4)
4. 🆕 **Update preprocessing integration** (Phase 4)
5. 🆕 **UI updates** (Phase 3)
6. 🆕 **Testing and rollout** (Phase 5)

---

**This hybrid approach gives users:**
- ✅ Fast, free optimization by default (pattern-based)
- ✅ Option for AI enhancement when needed
- ✅ Cost transparency and control
- ✅ Best of both worlds!



