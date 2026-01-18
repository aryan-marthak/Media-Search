r"""
Batch process images in D:\gallery\test with SmolVLM-500M
Generates descriptions for all images and saves to CSV
"""
import os
import time
import csv
from pathlib import Path
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForVision2Seq, BitsAndBytesConfig

# Configuration
TEST_FOLDER = r"D:\gallery\test"
OUTPUT_CSV = r"D:\gallery\test\descriptions.csv"

print("\n" + "="*80)
print("SmolVLM-500M Batch Description Generator")
print("="*80)

# Find all images
image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
image_files = []
for ext in image_extensions:
    image_files.extend(Path(TEST_FOLDER).glob(f"*{ext}"))
    image_files.extend(Path(TEST_FOLDER).glob(f"*{ext.upper()}"))

print(f"\nFound {len(image_files)} images in {TEST_FOLDER}")

if len(image_files) == 0:
    print("No images found! Exiting.")
    exit()

# Load SmolVLM-500M with 4-bit quantization
print("\nLoading SmolVLM-500M model...")
model_name = "HuggingFaceTB/SmolVLM-500M-Instruct"

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
)

processor = AutoProcessor.from_pretrained(
    model_name,
    size={"longest_edge": 384},
    do_image_splitting=False
)

model = AutoModelForVision2Seq.from_pretrained(
    model_name,
    quantization_config=quantization_config,
    device_map="auto"
)
model.eval()

print(">> Model loaded successfully!")

# Process images
results = []
total_time = 0

print(f"\nProcessing {len(image_files)} images...")
print("="*80)

for idx, image_path in enumerate(image_files, 1):
    try:
        # Load image
        image = Image.open(image_path).convert("RGB")
        
        # Generate description
        start = time.time()
        
        METADATA_PROMPT = """
        You are generating metadata to help a user find this image later.
        
        Rules:
        - Mention only what is visible or strongly suggested.
        - Do NOT invent facts.
        - If unsure, say "uncertain".
        - Use short phrases, not paragraphs.
        - If something might help identify the image later, include it.
        - If guessing, include a confidence score between 0.0 and 1.0.
        
        Tasks:
        1. Identify the main subjects.
        2. List secondary objects or elements.
        3. Describe the environment or setting.
        4. Note time-of-day or lighting if visible.
        5. Extract any visible text exactly as seen (partial is OK).
        6. Mention distinctive visual traits (clothing, colors, patterns, layout).
        7. Include uncertain hints only if helpful.
        
        Output STRICT JSON with keys:
        subjects,
        objects,
        environment,
        time_context,
        visible_text,
        distinctive_features,
        uncertain_hints
        """
        
        messages = [{
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": METADATA_PROMPT}
            ]
        }]

        
        prompt_text = processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = processor(text=prompt_text, images=[image], return_tensors="pt")
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=100, do_sample=False)
        
        generated_texts = processor.batch_decode(generated_ids, skip_special_tokens=True)
        description = generated_texts[0].split("Assistant:")[-1].strip()
        
        elapsed = time.time() - start
        total_time += elapsed
        
        # Store result
        results.append({
            'filename': image_path.name,
            'path': str(image_path),
            'description': description,
            'time_seconds': round(elapsed, 2)
        })
        
        # Print progress
        print(f"[{idx}/{len(image_files)}] {image_path.name}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Description: {description[:100]}{'...' if len(description) > 100 else ''}")
        print()
        
    except Exception as e:
        print(f"[{idx}/{len(image_files)}] ERROR processing {image_path.name}: {e}")
        results.append({
            'filename': image_path.name,
            'path': str(image_path),
            'description': f"ERROR: {str(e)}",
            'time_seconds': 0
        })

# Save to CSV
print("="*80)
print(f"\nSaving results to {OUTPUT_CSV}...")

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['filename', 'path', 'description', 'time_seconds'])
    writer.writeheader()
    writer.writerows(results)

print(f">> Results saved!")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total images processed: {len(results)}")
print(f"Successful: {sum(1 for r in results if not r['description'].startswith('ERROR'))}")
print(f"Failed: {sum(1 for r in results if r['description'].startswith('ERROR'))}")
print(f"Total time: {total_time:.2f}s")
print(f"Average time per image: {total_time/len(results):.2f}s")
print(f"\nResults saved to: {OUTPUT_CSV}")
print("="*80 + "\n")
