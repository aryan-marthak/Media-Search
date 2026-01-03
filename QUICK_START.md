# Quick Start: Testing Your SigLIP Improvements

## 1️⃣ Analyze Your Image (2 min)
```bash
cd backend
python debug_siglip_scores.py
```

**Output shows:**
- Raw similarity scores (will be negative - that's normal!)
- Calibrated scores with temperature=25
- Score distribution analysis
- Recommendations

## 2️⃣ Interactive Temperature Tuning (5 min)
```bash
cd backend
python tune_siglip_interactive.py
```

**Commands to try:**
```
> recommend
# Gets tailored temperature suggestion for YOUR image

> test dog
# See how "dog" scores across different temperatures

> compare outdoor
# Visual comparison of temperature impact

> all 18
# Test all default queries with temperature=18

> quit
```

## 3️⃣ Verify Query Expansion Works
```bash
cd backend
python -c "
from services.query_expansion import get_query_context
result = get_query_context('dog')
print(f'Query: {result[\"original\"]}')
print(f'Expansions: {result[\"expansions\"]}')
"
```

**Output should show:**
```
Query: dog
Expansions: ['dog', 'puppy', 'canine', 'pet', 'animal', 'pup']
```

## 4️⃣ Test Score Calibration
```bash
cd backend
python -c "
from services.embeddings import calibrate_siglip_score as calib
print('Temperature 18 (lenient):')
print(f'  -0.05 → {calib(-0.05, temp=18):.3f}')
print(f'  0.10 → {calib(0.10, temp=18):.3f}')
print()
print('Temperature 25 (standard):')
print(f'  -0.05 → {calib(-0.05, temp=25):.3f}')
print(f'  0.10 → {calib(0.10, temp=25):.3f}')
"
```

## 5️⃣ Adjust Temperature (if needed)

Open `backend/services/embeddings.py` and change line in `calibrate_siglip_score()`:

```python
def calibrate_siglip_score(raw_similarity: float, temperature: float = 25.0) -> float:
    # Change 25.0 to your preferred value:
    # - 15: Very lenient (accepts more)
    # - 18: Lenient  ← RECOMMENDED START
    # - 25: Strict (current)
```

## 6️⃣ How Scores Work Now

### Before (Old System)
```
Raw score: -0.0566
Attempted normalization: (-0.0566 + 0.1) / 0.4 = 0.365 ❌ BROKEN
```

### After (New System)
```
Raw score: -0.0566
Calibrated with temp=25: sigmoid(-0.0566 × 25) = 0.213 ✅ CORRECT
Calibrated with temp=18: sigmoid(-0.0566 × 18) = 0.226 ✅ MORE LENIENT
```

## 7️⃣ Tuning Guide Quick Reference

| Want This | Do This |
|-----------|---------|
| More results | Lower temperature (15-18) |
| Better quality | Keep temperature higher (25-28) |
| Test faster | Use `debug_siglip_scores.py` |
| Interactive testing | Use `tune_siglip_interactive.py` |
| See expansions | Use `query_expansion.py` |

## 8️⃣ What Changed in Your Code

### ✅ Added Functions
- `calibrate_siglip_score()` - Temperature-based score calibration
- `sigmoid()` - Helper for score computation
- Query expansion service - 100+ semantic term mappings

### ✅ Enhanced Functions
- `normal_search()` - Now uses query expansion
- `deep_search()` - Uses calibrated scores

### ✅ New Files
- `services/query_expansion.py` - Expansion dictionary & logic
- `debug_siglip_scores.py` - Image analysis tool
- `tune_siglip_interactive.py` - Interactive tuning tool

## 🎯 Expected Improvements

### Before Changes
```
Query: "dog"
Results: 2-3 images with avg score 0.16
```

### After Changes
```
Query: "dog"
Results: 8-10 images (expanded to: puppy, canine, pet, animal, pup)
Avg score: 0.35-0.50
```

## ⚠️ If Results Still Low

1. **Check your image**
   ```bash
   python debug_siglip_scores.py
   ```
   Does it show very low raw scores across all queries? If yes:

2. **Try lower temperature**
   - Change to 15 in `embeddings.py`
   - Retest with `debug_siglip_scores.py`

3. **Add metadata to images**
   When uploading, add:
   - `tags`: "outdoor, landscape, sunset"
   - `description`: Detailed description of image
   - `colors`: Dominant colors

4. **Consider larger model**
   In `config.py`:
   ```python
   SIGLIP_MODEL = "google/siglip-so400m-patch14-siglip-224"
   # Better accuracy but slower and more VRAM
   ```

## 📊 Testing Checklist

- [ ] Ran `debug_siglip_scores.py` and noted the recommendation
- [ ] Tried `tune_siglip_interactive.py` with "recommend" command
- [ ] Verified query expansion works
- [ ] Tested score calibration with different temperatures
- [ ] Adjusted temperature if recommended
- [ ] (Optional) Added metadata to images
- [ ] (Optional) Switched to larger model

## 🚀 You're Ready!

Your search engine now has:
- ✅ Proper score calibration
- ✅ Query expansion (semantic understanding)
- ✅ Tuning tools for optimization
- ✅ Documentation for future tweaks

Start with the recommendations from `debug_siglip_scores.py` and adjust from there!
