"""
Test BM25 scores for "group of friends people men" query
to determine optimal MIN_BM25_SCORE threshold
"""
import sys
sys.path.append('.')

from bm25_matcher import BM25Matcher

# Sample descriptions
descriptions = [
    "A group of people is gathered around a collection of motorcycles, with a prominent green one in the foreground. The motorcycles are parked on a red and blue striped carpet, and the people are engaged in conversation.",
    "A group of six men are sitting on a ledge, enjoying the sunset. They are dressed casually, with one man wearing a plaid shirt and another in a denim shirt. The cityscape in the background is bathed in the warm glow of the setting sun.",
    "In the image, a group of six young men are captured in a selfie, with the man in the center wearing a blue shirt and a black cap. The group is smiling and appears to be enjoying their time together.",
    "A group of friends standing together at a park, smiling and enjoying the day.",
    "Five men posing for a photo together, wearing casual clothes and standing close to each other."
]

query = "group of friends people men"

# Create BM25 matcher
matcher = BM25Matcher()
matcher.index_documents(descriptions)

# Get scores
results = matcher.search(query, top_k=len(descriptions))

print(f"\n{'='*80}")
print(f"Query: '{query}'")
print(f"{'='*80}\n")

# Normalize scores
max_score = max([score for _, score in results]) if results else 1.0

for idx, score in results:
    normalized = score / max_score
    desc_preview = descriptions[idx][:100] + "..." if len(descriptions[idx]) > 100 else descriptions[idx]
    
    print(f"Index: {idx}")
    print(f"Raw BM25 Score: {score:.4f}")
    print(f"Normalized Score: {normalized:.4f}")
    print(f"Description: {desc_preview}")
    
    # Check against current threshold
    if normalized >= 0.15:
        print(f"✅ PASSES current threshold (0.15)")
    else:
        print(f"❌ FILTERED by current threshold (0.15)")
    
    if normalized >= 0.25:
        print(f"✅ Would PASS with threshold 0.25")
    else:
        print(f"❌ Would be FILTERED with threshold 0.25")
    
    print(f"{'-'*80}\n")

print("\n📊 RECOMMENDATION:")
print("If motorcycle image (index 0) has normalized score >= 0.15, increase MIN_BM25_SCORE")
print("Suggested threshold: 0.25 or higher to filter weak matches")
