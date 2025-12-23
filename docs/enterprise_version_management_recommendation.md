# Enterprise Version Management: Best Practice Recommendations

## Current Problem Analysis

### The Issue
You're experiencing a **version mismatch** between initial ingestion and pipeline processing:

1. **Initial Ingest** (`sync_full`):
   - Uses: `version = request.version or (product.current_version + 1)`
   - Stores files with version X (e.g., 4)
   - Updates `product.current_version = X`

2. **Pipeline Trigger** (`trigger_pipeline`):
   - Uses: `version = request.version or (product.current_version + 1)`
   - Creates pipeline for version X+1 (e.g., 5)
   - But files exist for version X (4)

**Result**: Pipeline looks for version 5, but files only exist for version 4 → **Pipeline skips**

---

## Enterprise Best Practice: Version Resolution Strategy

### **Recommended Approach: Smart Version Resolution**

Based on enterprise data pipeline patterns (Airflow, AWS Data Pipeline, Google Cloud Dataflow), here's the recommended solution:

### **Strategy: Auto-Discover Latest Unprocessed Version**

When a pipeline is triggered **without explicit version**:

1. **Query `RawFile` table** for the product
2. **Find latest version** that has:
   - ✅ Raw files ingested (`status = INGESTED` or `PROCESSED`)
   - ✅ No successful pipeline run yet (or pipeline failed and needs retry)
3. **Use that version** for pipeline processing

### **Why This Works**

✅ **Convenient**: No need to manually specify version  
✅ **Safe**: Always processes available data  
✅ **Explicit**: Still allows version override when needed  
✅ **Traceable**: Clear relationship between ingestion and processing  
✅ **Idempotent**: Can reprocess same version if needed  

---

## Recommended Implementation Options

### **Option A: Auto-Use Latest Ingested Version (Recommended)**

**Behavior**:
- **If `version` is explicitly provided**: Use that version (fail if no raw files)
- **If `version` is `None`**: Auto-detect latest version with raw files

**Implementation**:
```python
# In trigger_pipeline endpoint
if request.version is None:
    # Auto-discover latest version with raw files
    latest_raw_file = db.query(RawFile).filter(
        RawFile.product_id == product.id,
        RawFile.status.in_([RawFileStatus.INGESTED, RawFileStatus.PROCESSED])
    ).order_by(RawFile.version.desc()).first()
    
    if not latest_raw_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No raw files found. Please run initial ingestion first."
        )
    
    version = latest_raw_file.version
    logger.info(f"Auto-detected latest ingested version: {version}")
else:
    # Use explicit version
    version = request.version
    # Verify raw files exist for this version
    raw_file_count = db.query(RawFile).filter(
        RawFile.product_id == product.id,
        RawFile.version == version
    ).count()
    
    if raw_file_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No raw files found for version {version}. "
                   f"Please run initial ingestion for this version first."
        )
```

**Pros**:
- ✅ User-friendly: "Just click run" without thinking about versions
- ✅ Automatic: Always processes latest data
- ✅ Still allows explicit version control

**Cons**:
- ⚠️ Less explicit: User might not know which version is being processed
- ⚠️ Could reprocess old data if latest version already processed

---

### **Option B: Auto-Use Latest Unprocessed Version (Better)**

**Behavior**:
- **If `version` is explicitly provided**: Use that version
- **If `version` is `None`**: Use latest version that has raw files BUT no successful pipeline run

**Implementation**:
```python
if request.version is None:
    # Find latest version with raw files but no successful pipeline
    from primedata.db.models import PipelineRun, PipelineRunStatus
    
    # Get all versions with raw files
    versions_with_files = db.query(
        RawFile.version
    ).filter(
        RawFile.product_id == product.id,
        RawFile.status.in_([RawFileStatus.INGESTED, RawFileStatus.FAILED])
    ).distinct().order_by(RawFile.version.desc()).all()
    
    # Filter out versions that already succeeded
    for (version_with_files,) in versions_with_files:
        existing_run = db.query(PipelineRun).filter(
            PipelineRun.product_id == product.id,
            PipelineRun.version == version_with_files,
            PipelineRun.status == PipelineRunStatus.SUCCEEDED
        ).first()
        
        if not existing_run:
            version = version_with_files
            logger.info(f"Auto-detected latest unprocessed version: {version}")
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All ingested versions have been processed. "
                   "Please run initial ingestion to create a new version."
        )
```

**Pros**:
- ✅ Smart: Avoids reprocessing already-processed versions
- ✅ Efficient: Only processes what needs processing
- ✅ User-friendly: Still automatic

**Cons**:
- ⚠️ More complex logic
- ⚠️ May skip failed runs (though you can include FAILED in the query)

---

### **Option C: Use Latest Ingested Version OR Explicit Override (Hybrid - Best)**

**Behavior**:
- **If `version` is explicitly provided**: Use that version (with validation)
- **If `version` is `None`**: Use latest ingested version
- **Always validate**: Check that raw files exist for the version

**Implementation**:
```python
# Determine version
if request.version is not None:
    # Explicit version provided - validate it exists
    version = request.version
    raw_file_count = db.query(RawFile).filter(
        RawFile.product_id == product.id,
        RawFile.version == version
    ).count()
    
    if raw_file_count == 0:
        # Provide helpful error message
        latest_version = db.query(
            func.max(RawFile.version)
        ).filter(
            RawFile.product_id == product.id
        ).scalar()
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": f"No raw files found for version {version}",
                "requested_version": version,
                "latest_ingested_version": latest_version,
                "suggestion": f"Please run initial ingestion for version {version}, "
                             f"or use version={latest_version} to process latest ingested data"
            }
        )
else:
    # Auto-detect: Use latest version with raw files
    latest_raw_file = db.query(RawFile).filter(
        RawFile.product_id == product.id,
        RawFile.status.in_([RawFileStatus.INGESTED, RawFileStatus.FAILED])
    ).order_by(RawFile.version.desc()).first()
    
    if not latest_raw_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No raw files found. Please run initial ingestion first."
        )
    
    version = latest_raw_file.version
    logger.info(f"Auto-selected latest ingested version: {version} (found {latest_raw_file.filename})")
```

**Pros**:
- ✅ Best of both worlds: Automatic + explicit control
- ✅ Helpful errors: Guides user to correct action
- ✅ Validates: Always checks raw files exist

**Cons**:
- ⚠️ Slightly more code complexity

---

## Recommended Workflow

### **Ideal User Experience**

1. **User runs initial ingestion** → Files stored with version X
2. **User clicks "Run Pipeline"** (no version specified)
3. **System automatically**:
   - Finds latest ingested version (X)
   - Validates raw files exist
   - Starts pipeline for version X
4. **Pipeline processes** version X files
5. **Result**: Seamless, no version coordination needed

### **Advanced Use Case**

1. **User wants to reprocess version 3** (explicit):
   - User specifies `version=3` in API call
   - System validates version 3 has raw files
   - Starts pipeline for version 3
   - ✅ Works even if version 4 or 5 exist

---

## Comparison Table

| Approach | User Experience | Complexity | Flexibility | Recommendation |
|----------|----------------|------------|-------------|----------------|
| **Current** (always +1) | ❌ Manual coordination needed | Low | Low | ❌ Not enterprise-ready |
| **Option A** (latest ingested) | ✅ Automatic | Medium | Medium | ✅ Good |
| **Option B** (latest unprocessed) | ✅ Automatic + Smart | High | Medium | ✅✅ Better |
| **Option C** (auto + override) | ✅✅ Best UX | Medium | High | ✅✅✅ **Best** |

---

## Enterprise Pattern Reference

This pattern aligns with:

1. **Apache Airflow**: Auto-detects latest unprocessed data partitions
2. **AWS Glue**: Uses `latest` as default partition value
3. **Google Cloud Dataflow**: Auto-discovers latest input files
4. **dbt**: Uses `--select` with auto-detection of latest models

---

## Recommendation

### **Implement Option C (Hybrid Approach)**

**Why**:
- ✅ **User-friendly**: Default behavior "just works"
- ✅ **Flexible**: Allows explicit version control when needed
- ✅ **Enterprise-grade**: Follows industry patterns
- ✅ **Self-healing**: Provides helpful error messages

**Key Benefits**:
1. **No manual coordination**: User doesn't need to track versions
2. **Explicit when needed**: Can still override for reprocessing
3. **Better errors**: Guides users to correct action
4. **Production-ready**: Handles edge cases gracefully

---

## Implementation Priority

### **Phase 1: Critical (Do Now)**
1. ✅ Implement Option C: Auto-detect latest ingested version
2. ✅ Validate raw files exist before starting pipeline
3. ✅ Provide helpful error messages with version suggestions

### **Phase 2: Enhancement (Next Sprint)**
4. ✅ Option B enhancement: Skip already-processed versions
5. ✅ UI indication: Show which version will be processed
6. ✅ Version dropdown: Let users select from available versions

### **Phase 3: Advanced (Future)**
7. ✅ Version comparison: Show diff between versions
8. ✅ Reprocess options: "Reprocess last failed" vs "Process new"
9. ✅ Batch processing: Process multiple versions in sequence

---

## Answer to Your Question

**Q: "Should we have to run initial ingestion every time before running the pipeline?"**

**A: No, with Option C implementation:**

- ✅ **First time**: Run initial ingestion → then pipeline automatically picks it up
- ✅ **Subsequent times**: Just run pipeline → it auto-uses latest ingested version
- ✅ **Reprocessing**: Specify version explicitly if needed

**The system becomes self-coordinating!**

---

## Next Steps

1. Review this recommendation
2. Choose implementation option (recommended: Option C)
3. Implement the version resolution logic
4. Test with your workflow
5. Update UI to show auto-selected version

**This will make the system truly enterprise-ready!** 🚀


