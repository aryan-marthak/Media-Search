# SigLIP Score Improvement Guide

## Problem Analysis
Your debug results show:
- **Raw similarity scores**: -0.0918 to -0.0011 (all negative/near-zero)
- **Calibrated scores**: 0.0916 to 0.4933 (very low confidence range)
- **Variance**: Only 0.0256 - the model can't distinguish queries well

This indicates the image content doesn't naturally align with semantic text queries.

## Root Causes & Solutions

### 1. **Image Metadata Issue** ❌
Raw embeddings alone may be insufficient. The image needs contextual metadata.

**Solution**: Add image metadata enrichment
```python
# Add to image processing pipeline
metadata = {
    "filename": "image.jpg",
    "upload_date": "2024-01-15",
    "tags": "outdoor, nature, landscape",  # Add semantic tags
    "description": "Mountain landscape at sunset",  # Add description
    "width": 1920,
    "height": 1080,
    "colors": ["blue", "orange", "green"]  # Dominant colors
}
```

### 2. **Model Fine-tuning** ⚙️
SigLIP-base might not be optimal for your domain.

**Options**:
- Use `google/siglip-large-patch16-256` (larger, more accurate but slower)
- Use `google/siglip-so400m-patch14-siglip-224` (very good balance)
- Fine-tune on your own image-description pairs

### 3. **Query Expansion** 📝
Expand queries to include synonyms and related terms.

**Example**:
```python
# Instead of just searching "dog"
# Also search "puppy", "canine", "pet", "animal"

QUERY_EXPANSIONS = {
    "dog": ["dog", "puppy", "canine", "pet", "animal"],
    "person": ["person", "people", "human", "face", "portrait"],
    "outdoor": ["outdoor", "nature", "landscape", "outside", "exterior"],
}
```

### 4. **Hybrid Search** 🔀
Combine embeddings with metadata/full-text search.

**Current**: 60% embeddings + 40% metadata
**Better**: 40% embeddings + 40% metadata + 20% keyword matching

### 5. **Score Calibration Adjustment** 📊
Your current temperature (25) might be too aggressive for negative scores.

**Recommendations**:
- For general search: temperature = 15-20 (more lenient)
- For strict filtering: temperature = 25-30 (more selective)

## Implementation Steps

### Step 1: Add Image Metadata Enrichment
See `services/metadata_enrichment.py` (create this new file)

### Step 2: Update Search Pipeline
Modify search.py to use enriched metadata

### Step 3: Implement Query Expansion
Create query expansion service

### Step 4: Test & Iterate
Use debug_siglip_scores.py to verify improvements

## Immediate Quick Wins

1. **Lower temperature from 25 to 18** - More lenient scoring
2. **Add description/tags to images** - Better metadata matching
3. **Switch to larger SigLIP model** - Better semantic understanding
4. **Use query expansion** - Catch variations of search terms

## Performance Impact

| Approach | Speed | Accuracy | Memory |
|----------|-------|----------|--------|
| Current embeddings only | ⚡⚡⚡ | ⭐⭐ | 📦 |
| + Metadata matching | ⚡⚡ | ⭐⭐⭐ | 📦 |
| + Query expansion | ⚡ | ⭐⭐⭐⭐ | 📦 |
| Larger SigLIP model | ⚡ | ⭐⭐⭐⭐ | 📦📦 |

## Next Steps

1. Start with query expansion (easiest, quick win)
2. Add metadata enrichment for new images
3. Test larger SigLIP model if scores don't improve
4. Consider fine-tuning if building special domain
