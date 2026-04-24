"""
Standalone Flickr8k Evaluation Script for Google Colab
------------------------------------------------------
Since the original evaluate_metrics.py strictly calls the /search and 
/deep-search REST APIs relying on Qdrant, PostgreSQL, and Redis, 
it cannot be run directly on Colab easily.

This script completely replicates the logic of the FastAPI backend 
(embedding_service.py and vlm_service.py) into a pure, standalone 
PyTorch script optimized for a Colab notebook instance.

Instructions for Google Colab:
1. Upload your Flickr8k 'Images' folder and 'captions.txt' to Colab.
2. Run a cell to install requirements:
   !pip install torch torchvision open_clip_torch transformers accelerate bitsandbytes rank_bm25 tqdm pillow
3. Run this script:
   !python colab_flickr8k_eval.py --images-dir /content/Images --captions-file /content/captions.txt
"""

import os
import csv
import torch
import open_clip
import argparse
import numpy as np
from PIL import Image
from tqdm import tqdm

from transformers import Idefics3Processor, Idefics3ForConditionalGeneration, BitsAndBytesConfig
from rank_bm25 import BM25Okapi

# Constants
CLIP_MODEL_NAME = "ViT-L-14"
CLIP_PRETRAINED = "openai"
VLM_MODEL_NAME = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"

TOP_K = 30
GLOBAL_WEIGHT = 0.6
LOCAL_WEIGHT = 0.4
BM25_WEIGHT = 0.7
CLIP_WEIGHT = 0.3

# Evaluation Helper Functions (copied from evaluate_metrics.py)
def precision_at_k(retrieved, relevant, k):
    if k == 0: return 0.0
    top_k = retrieved[:k]
    hits = len(set(top_k) & set(relevant))
    return hits / k

def recall_at_k(retrieved, relevant, k):
    if not relevant: return 0.0
    top_k = retrieved[:k]
    hits = len(set(top_k) & set(relevant))
    return hits / len(relevant)

def average_precision(retrieved, relevant):
    if not relevant: return 0.0
    rel_count = 0
    prec_sum = 0.0
    for i, img_id in enumerate(retrieved):
        if img_id in relevant:
            rel_count += 1
            prec_sum += rel_count / (i + 1)
    if rel_count == 0: return 0.0
    return prec_sum / len(relevant)


def get_image_crops(image: Image.Image):
    """Generates 5 crops: 1 center crop and 4 quadrant crops."""
    width, height = image.size
    crops = []
    
    # 1. Center Crop (60% of shorter dimension)
    short_dim = min(width, height)
    center_size = int(short_dim * 0.6)
    left = (width - center_size) // 2
    top = (height - center_size) // 2
    right = left + center_size
    bottom = top + center_size
    crops.append(image.crop((left, top, right, bottom)))
    
    # Quadrants (50% of the image)
    half_w, half_h = width // 2, height // 2
    crops.append(image.crop((0, 0, half_w, half_h)))                  # Top-Left
    crops.append(image.crop((half_w, 0, width, half_h)))              # Top-Right
    crops.append(image.crop((0, half_h, half_w, height)))             # Bottom-Left
    crops.append(image.crop((half_w, half_h, width, height)))         # Bottom-Right
    
    return crops

def main(args):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Running evaluation on device: {device}")

    # =========================================================================
    # 1. LOAD DATASET
    # =========================================================================
    image_to_captions = {}
    with open(args.captions_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) < 2: continue
            img_name, caption = row[0].strip(), row[1].strip()
            # Only consider images that actually exist in the folder
            if os.path.isfile(os.path.join(args.images_dir, img_name)):
                image_to_captions.setdefault(img_name, []).append(caption)

    # Limit to N images if specified
    all_images = list(image_to_captions.keys())
    
    if len(all_images) == 0:
        print(f"\n[ERROR] Found 0 images. We checked the directory '{args.images_dir}' using names from '{args.captions_file}'.")
        print("Please verify:")
        print(f"1. Does the directory '{args.images_dir}' actually contain the .jpg files, or is it in a subfolder?")
        print(f"2. Are the paths case-sensitive? Colab (Linux) cares about case ('Images' != 'images').")
        import sys; sys.exit(1)
        
    if args.max_images > 0:
        all_images = all_images[:args.max_images]
        image_to_captions = {k: image_to_captions[k] for k in all_images}
    
    print(f"Dataset Loaded: {len(all_images)} images, {sum(len(v) for v in image_to_captions.values())} queries.")

    # =========================================================================
    # 2. LOAD CLIP AND PRECOMPUTE EMBEDDINGS (GLOBAL + CROPS)
    # =========================================================================
    print("Loading CLIP Model (ViT-L-14)...")
    clip_model, _, preprocess = open_clip.create_model_and_transforms(CLIP_MODEL_NAME, pretrained=CLIP_PRETRAINED, device=device)
    tokenizer = open_clip.get_tokenizer(CLIP_MODEL_NAME)
    
    image_embeddings = {}
    crop_embeddings = {}  # Cache crop embeddings to save 113 hours!
    
    print("Computing global & local crop embeddings for all images (this takes ~15 mins)...")
    with torch.no_grad():
        for img_name in tqdm(all_images):
            img_path = os.path.join(args.images_dir, img_name)
            try:
                image = Image.open(img_path).convert("RGB")
                
                # Global Embedding
                img_tensor = preprocess(image).unsqueeze(0).to(device)
                feat = clip_model.encode_image(img_tensor)
                feat = feat / feat.norm(dim=-1, keepdim=True)
                image_embeddings[img_name] = feat.cpu().numpy()[0]
                
                if args.mode == "standard":
                    # Pre-calculate the 5 crops for Re-ranking
                    crops = get_image_crops(image)
                    crop_inputs = torch.cat([preprocess(c).unsqueeze(0) for c in crops]).to(device)
                    c_feats = clip_model.encode_image(crop_inputs)
                    c_feats = c_feats / c_feats.norm(dim=-1, keepdim=True)
                    crop_embeddings[img_name] = c_feats.cpu().numpy()
            except Exception as e:
                print(f"Error processing {img_name}: {e}")
                
    # Store global matrix for fast cosine similarity
    img_names_array = list(image_embeddings.keys())
    img_matrix = np.array([image_embeddings[k] for k in img_names_array])

    # =========================================================================
    # 3. CONFIGURE VLM & BM25 (IF DEEP SEARCH)
    # =========================================================================
    image_descriptions = {}
    bm25 = None
    if args.mode == "deep":
        print("Loading SmolVLM for deep search hybrid captions (this will take a while)...")
        # 4-bit quantization helps load it on Colab T4 GPUs
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )
        processor = Idefics3Processor.from_pretrained(VLM_MODEL_NAME, trust_remote_code=True)
        vlm_model = Idefics3ForConditionalGeneration.from_pretrained(
            VLM_MODEL_NAME, quantization_config=quant_config, device_map="auto", trust_remote_code=True
        )
        vlm_model.eval()

        print("Generating VLM Descriptions...")
        for img_name in tqdm(all_images):
            img_path = os.path.join(args.images_dir, img_name)
            image = Image.open(img_path).convert("RGB")
            messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": "Describe this image in extreme detail."}]}]
            text_prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
            inputs = processor(text=text_prompt, images=[image], return_tensors="pt")
            inputs = {k: v.to(vlm_model.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = vlm_model.generate(**inputs, max_new_tokens=150)
            
            desc = processor.decode(outputs[0], skip_special_tokens=True).split("Assistant:")[-1].strip()
            image_descriptions[img_name] = desc

        # Build BM25 Index
        corpus = [desc.lower().split() for desc in image_descriptions.values()]
        bm25 = BM25Okapi(corpus)

    # =========================================================================
    # 4. RUN QUERIES AND EVALUATE
    # =========================================================================
    # Prepare all queries and their ground truth matches
    queries = []
    for img_name, captions in image_to_captions.items():
        for cap in captions:
            queries.append({"query": cap, "ground_truth": [img_name]})
    
    print(f"Running evaluation on {len(queries)} queries...")
    
    p5_sum, r20_sum, ap_sum, successes = 0.0, 0.0, 0.0, 0
    errors = 0

    for i, q in enumerate(tqdm(queries)):
        query_text = q["query"]
        expected = q["ground_truth"]

        # 4a. Encode Text Query
        with torch.no_grad():
            text_tokens = tokenizer([query_text]).to(device)
            feat = clip_model.encode_text(text_tokens)
            feat = feat / feat.norm(dim=-1, keepdim=True)
            query_emb = feat.cpu().numpy()[0]
        
        # 4b. Global Semantic Retrieval (Cosine Similarity)
        similarities = np.dot(img_matrix, query_emb)
        
        # Mode 0: Global-Only Baseline
        if args.mode == "baseline":
            top_indices = np.argsort(similarities)[::-1][:TOP_K]
            retrieved_ids = [img_names_array[idx] for idx in top_indices]
            
        # Mode 1: Standard Re-Ranking
        elif args.mode == "standard":
            # Get top global candidates
            top_indices = np.argsort(similarities)[::-1][:TOP_K]
            candidates = [img_names_array[idx] for idx in top_indices]
            global_scores = [similarities[idx] for idx in top_indices]
            
            final_scores = []
            for candidate_name, g_score in zip(candidates, global_scores):
                # Apply Local Crop Re-ranking using cache
                try:
                    crop_embs = crop_embeddings[candidate_name]
                    local_scores = np.dot(crop_embs, query_emb)
                    max_local_score = float(np.max(local_scores))
                    hybrid_score = (GLOBAL_WEIGHT * float(g_score)) + (LOCAL_WEIGHT * max_local_score)
                    final_scores.append((candidate_name, hybrid_score))
                except KeyError:
                    final_scores.append((candidate_name, float(g_score))) # fallback
            
            # Rank candidates
            final_scores.sort(key=lambda x: x[1], reverse=True)
            retrieved_ids = [k for k, v in final_scores]
            
        elif args.mode == "deep":
            # Mode 3: BM25 + CLIP Hybrid Search
            q_terms = query_text.lower().split()
            bm25_scores = bm25.get_scores(q_terms)
            
            max_b_score = np.max(bm25_scores) if np.max(bm25_scores) > 0 else 1.0
            norm_bm25 = bm25_scores / max_b_score
            
            hybrid_scores = (BM25_WEIGHT * norm_bm25) + (CLIP_WEIGHT * similarities)
            top_indices = np.argsort(hybrid_scores)[::-1][:TOP_K]
            retrieved_ids = [img_names_array[idx] for idx in top_indices]

        # Calculate Metrics
        p5 = precision_at_k(retrieved_ids, expected, k=5)
        r20 = recall_at_k(retrieved_ids, expected, k=20)
        ap = average_precision(retrieved_ids, expected)

        p5_sum += p5
        r20_sum += r20
        ap_sum += ap
        
        # Success = relevant image found in top 3
        if set(retrieved_ids[:3]) & set(expected):
            successes += 1

    total_eval = len(queries)
    print("\n" + "="*50)
    print(f"RESULTS FOR {args.mode.upper()} MODE")
    print("="*50)
    print(f"Precision@5       : {p5_sum / total_eval:.4f}")
    print(f"Recall@20         : {r20_sum / total_eval:.4f}")
    print(f"mAP               : {ap_sum / total_eval:.4f}")
    print(f"Query Success Rate: {(successes / total_eval)*100:.1f}%")
    print("="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--images-dir", required=True, help="Path to Flickr8k 'Images' folder")
    parser.add_argument("--captions-file", required=True, help="Path to 'captions.txt'")
    parser.add_argument("--mode", required=True, choices=["baseline", "standard", "deep"], help="Search mode")
    parser.add_argument("--max-images", type=int, default=0, help="Limit number of images evaluated")
    args = parser.parse_args()
    main(args)
