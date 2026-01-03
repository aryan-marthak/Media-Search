"""
Debug script to analyze SigLIP embedding scores.
Tests real image-text similarity and score calibration.
"""
import os
import numpy as np
from PIL import Image
from services.embeddings import encode_text, encode_image, calibrate_siglip_score

# Test queries with expected good matches
TEST_CASES = [
    ("dog", ["dog", "puppy", "animal", "pet"]),
    ("outdoor", ["nature", "landscape", "sky", "outdoor", "trees"]),
    ("food", ["food", "eating", "meal", "restaurant", "dinner"]),
    ("person", ["person", "people", "human", "face", "portrait"]),
]

# Negative queries (should have low similarity)
NEGATIVE_TESTS = [
    ("car", "dog"),
    ("mountain", "interior"),
    ("food", "building"),
]


def analyze_image_text_similarity():
    """Test image-text similarity with calibration."""
    
    img_path = r"D:\Media-Search\data\images\c7e1dc1c-dc3c-420b-9f47-8cd297fd02cb"
    
    if not os.path.exists(img_path):
        print(f"❌ Image directory not found: {img_path}")
        return
    
    files = [f for f in os.listdir(img_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    if not files:
        print(f"❌ No images found in {img_path}")
        return
    
    # Use first image
    test_img_path = os.path.join(img_path, files[0])
    print(f"📷 Testing with image: {files[0]}\n")
    
    # Load and encode image
    test_img = Image.open(test_img_path).convert("RGB")
    img_emb = encode_image(test_img)
    
    print(f"Image embedding shape: {img_emb.shape}")
    print(f"Image embedding norm: {np.linalg.norm(img_emb):.4f}")
    print(f"Image embedding stats: min={img_emb.min():.4f}, max={img_emb.max():.4f}, mean={img_emb.mean():.4f}\n")
    
    # Test various queries
    print("=" * 80)
    print("QUERY SIMILARITY ANALYSIS")
    print("=" * 80)
    
    queries_to_test = [
        "a photo", "person", "outdoor", "dog", "food", 
        "abstract art", "architecture", "nature scene",
        "random words xyz", "test query"
    ]
    
    scores = []
    for query in queries_to_test:
        q_emb = encode_text(query)
        raw_sim = np.dot(img_emb, q_emb)
        calibrated_sim = calibrate_siglip_score(raw_sim)
        scores.append(raw_sim)
        
        print(f"Query: '{query:20}' | Raw: {raw_sim:7.4f} | Calibrated: {calibrated_sim:.4f}")
    
    print("\n" + "=" * 80)
    print("SCORE DISTRIBUTION ANALYSIS")
    print("=" * 80)
    print(f"Raw similarity stats:")
    print(f"  Min: {min(scores):.4f}")
    print(f"  Max: {max(scores):.4f}")
    print(f"  Mean: {np.mean(scores):.4f}")
    print(f"  Std: {np.std(scores):.4f}")
    print(f"  Median: {np.median(scores):.4f}")
    
    # Calibrated versions
    calibrated_scores = [calibrate_siglip_score(s) for s in scores]
    print(f"\nCalibrated similarity stats:")
    print(f"  Min: {min(calibrated_scores):.4f}")
    print(f"  Max: {max(calibrated_scores):.4f}")
    print(f"  Mean: {np.mean(calibrated_scores):.4f}")
    print(f"  Std: {np.std(calibrated_scores):.4f}")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    # Analyze score ranges
    mean_score = np.mean(scores)
    std_score = np.std(scores)
    
    if std_score < 0.05:
        print("⚠️  Very low score variance - embeddings may be nearly identical")
        print("   Action: Try different image or verify model is loaded correctly")
    elif mean_score < 0.1:
        print("⚠️  Low average raw similarity scores")
        print("   Action: May need to increase temperature in calibration (currently 25)")
        print("   Try increasing temperature to 30-35 for more lenient scoring")
    elif mean_score > 0.4:
        print("✅ Good score distribution - embeddings are reasonably diverse")
    else:
        print("✅ Normal score distribution - consider current calibration appropriate")
    
    return img_emb, scores


def test_temperature_impact():
    """Test how temperature affects score calibration."""
    print("\n" + "=" * 80)
    print("TEMPERATURE IMPACT ANALYSIS")
    print("=" * 80)
    
    # Use sample scores from typical range
    sample_scores = [-0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    temperatures = [10, 15, 20, 25, 30, 35]
    
    print("\nHow different temperatures affect score calibration:")
    print("(Each row is a raw similarity score)\n")
    
    print(f"{'Raw Score':<12}", end="")
    for temp in temperatures:
        print(f"Temp={temp:<4}", end="  ")
    print()
    print("-" * 70)
    
    for score in sample_scores:
        print(f"{score:<12.2f}", end="")
        for temp in temperatures:
            calibrated = calibrate_siglip_score(score, temperature=temp)
            print(f"{calibrated:<9.3f}", end="  ")
        print()
    
    print("\n💡 Tips:")
    print("  - Lower temperature (10-15): More conservative, higher thresholds")
    print("  - Higher temperature (30-35): More lenient, broader acceptance range")
    print("  - Default (25): Balanced approach")


if __name__ == "__main__":
    print("\n🔍 SigLIP Score Debug & Analysis Tool\n")
    
    try:
        img_emb, raw_scores = analyze_image_text_similarity()
        test_temperature_impact()
        
        print("\n" + "=" * 80)
        print("✅ Debug analysis complete!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
