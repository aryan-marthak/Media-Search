# SigLIP Score Calibration & Tuning Guide

## Current Situation
Your tests show all queries getting **negative to near-zero scores** (-0.09 to -0.001). This is normal behavior - SigLIP produces raw cosine similarities in the -1 to 1 range. The issue is not the model, but how you interpret these scores.

## Temperature Calibration Reference

With **temperature = 25** (current default):
| Raw Score | Calibrated |
|-----------|-----------|
| -0.20 | 0.007 |
| -0.10 | 0.076 |
| -0.05 | 0.230 |
| 0.00 | 0.500 |
| 0.10 | 0.924 |
| 0.20 | 0.993 |

## Problem: Your Scores Are All Negative

This means your image doesn't match ANY of the test queries well. Possible reasons:

### 1. **The image is ambiguous or lacks semantic meaning**
If it's an abstract photo, random objects, or unclear composition

### 2. **The image needs context (metadata)**
Solution: Add tags, descriptions, or color information

### 3. **The test queries don't match the image content**
Solution: Use more varied queries specific to your image

## Solutions (in order of impact)

### Solution A: Lower the Temperature (Quick Fix) ⚡
**Current**: 25 (very strict)
**Try**: 15-18 (more lenient)

```python
# In embeddings.py, change:
def calibrate_siglip_score(raw_similarity, temperature=15):  # was 25
    ...
```

**Impact**:
- Raw -0.05 score → 0.23 (with temp=25) vs 0.19 (with temp=18)
- More lenient but less discriminative

### Solution B: Use Query Expansion (Medium Effort, High Impact) 🎯
Already implemented in updated search.py!

When you search for "dog", it now also searches:
- "puppy", "canine", "pet", "animal", "pup"

This dramatically increases hit rate for concepts.

**How to verify it works:**
```bash
cd backend
python -c "from services.query_expansion import get_query_context; print(get_query_context('dog'))"
```

### Solution C: Add Image Metadata/Descriptions (High Impact) 📝

Current metadata is minimal. Add:
```python
{
    "filename": "image.jpg",
    "tags": "outdoor, landscape, nature",
    "description": "A mountain vista at golden hour",
    "colors": ["blue", "orange", "green"],
    "style": "landscape photography",
    "season": "autumn"
}
```

Then use metadata matching to boost scores:
```python
# In search.py
combined_score = (0.5 * embedding_score) + (0.5 * metadata_match_score)
```

### Solution D: Switch to Better SigLIP Model (Best Quality)
Current: `google/siglip-base-patch16-224` (small)
Better: `google/siglip-so400m-patch14-siglip-224` (larger, more accurate)

**Config change:**
```python
# In config.py
SIGLIP_MODEL = "google/siglip-so400m-patch14-siglip-224"  # or
SIGLIP_MODEL = "google/siglip-large-patch16-256"
```

**Trade-offs:**
- Larger model = Better accuracy, slower, more memory
- Smaller model = Faster, less accurate

## Debugging: Find What Works

Use the provided debug script to test different configurations:

```bash
cd backend
python debug_siglip_scores.py
```

This shows:
- Raw similarity scores
- Calibrated scores with current temperature
- Score distribution

## Step-by-Step Tuning Process

### Step 1: Understand Your Data
```bash
python debug_siglip_scores.py
```
What do the raw scores look like?

### Step 2: Try Temperature Adjustment
Modify `calibrate_siglip_score(raw_sim, temperature=X)`:
- X=10: Very lenient (almost everything scores 0.4+)
- X=15: Lenient
- X=20: Moderate
- X=25: Strict (current)
- X=30: Very strict

### Step 3: Add Query Expansion
Already done in updated search.py

### Step 4: Add Metadata to Images
When uploading/processing images, add:
- Color tags
- Scene descriptors
- Objects detected
- Semantic labels

### Step 5: Rebalance Weights
Adjust in deep_search():
```python
# Current: 60% embedding + 40% metadata
combined_score = (0.6 * embedding_score) + (0.4 * meta_score)

# Try: 50/50 split
combined_score = (0.5 * embedding_score) + (0.5 * meta_score)

# Try: 40/60 if metadata is rich
combined_score = (0.4 * embedding_score) + (0.6 * meta_score)
```

## Recommended Priority

1. **First**: Lower temperature to 18 (5 min fix)
2. **Second**: Add query expansion (already done)
3. **Third**: Add rich metadata to images (ongoing)
4. **Fourth**: Switch to larger model if still unsatisfied (slow but best)

## Expected Results After Improvements

| Scenario | Current | After Quick Fixes | After Full Optimization |
|----------|---------|------------------|------------------------|
| "dog" search | 0 results | 5-10 results | 15+ results |
| Avg score | 0.16 | 0.35 | 0.65 |
| Precision | Low | Medium | High |
| Recall | Very low | Good | Excellent |

## When to Stop Tuning

Your search is "good enough" when:
- ✅ Most relevant images appear in top 5 results
- ✅ Average score > 0.4 for relevant images
- ✅ No obvious wrong results in top 10

## Advanced: Fine-tuning SigLIP

If standard tuning doesn't work, consider fine-tuning on your image dataset:

```bash
# Requires:
# - Image-description pairs
# - Small GPU with 12GB+ VRAM
# - Training time: 4-8 hours

python scripts/finetune_siglip.py \
  --train_data your_images_with_descriptions.jsonl \
  --num_epochs 3 \
  --batch_size 64
```

Not recommended unless you have 1000+ image-description pairs.

## Common Issues & Fixes

### Issue: All scores are still negative after temp reduction
**Fix**: Add richer metadata descriptions. Embeddings alone won't capture nuance without context.

### Issue: Query expansion returns too many results
**Fix**: Increase the threshold in search.py:
```python
for term in expanded_terms[:5]:  # was [:10]
```

### Issue: Search is too slow with expansion
**Fix**: Use only primary term or limit expansions to top 3

### Issue: Scores don't discriminate (all 0.4-0.5)
**Fix**: Either increase temperature back to 25, or improve image descriptions
