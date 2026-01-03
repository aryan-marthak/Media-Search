"""Check text vs image embedding similarity."""
from qdrant_client import QdrantClient
from services.embeddings import encode_text, encode_image
from PIL import Image
import numpy as np

# Load a test image
img_path = r"D:\Media-Search\data\images\c7e1dc1c-dc3c-420b-9f47-8cd297fd02cb"
import os
files = os.listdir(img_path)
print(f"Found {len(files)} images")

# Get one image
test_img = Image.open(os.path.join(img_path, files[0])).convert("RGB")
print(f"Test image: {files[0]}")

# Get embeddings
img_emb = encode_image(test_img)
text_emb = encode_text("a photo")

# Check properties
print(f"\nImage embedding norm: {np.linalg.norm(img_emb):.4f}")
print(f"Text embedding norm: {np.linalg.norm(text_emb):.4f}")

# Cosine similarity
cos_sim = np.dot(img_emb, text_emb) / (np.linalg.norm(img_emb) * np.linalg.norm(text_emb))
print(f"Cosine similarity (image vs 'a photo'): {cos_sim:.4f}")

# Try a few queries
for query in ["people", "train", "sunset", "mountain", "outdoor"]:
    q_emb = encode_text(query)
    cos = np.dot(img_emb, q_emb) / (np.linalg.norm(img_emb) * np.linalg.norm(q_emb))
    print(f"Similarity vs '{query}': {cos:.4f}")
