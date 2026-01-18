r"""
Enhanced batch image description with OCR for license plates and text
Uses SmolVLM-500M + EasyOCR for better text detection
"""
import os
import time
import csv
import json
from pathlib import Path
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForVision2Seq, BitsAndBytesConfig

# Try to import EasyOCR for text detection
try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print(">> EasyOCR not installed. Install with: pip install easyocr")

# Configuration
TEST_FOLDER = r"D:\gallery\test"
OUTPUT_CSV = r"D:\gallery\test\descriptions_enhanced.csv"

print("\n" + "="*80)
print("Enhanced Image Description Generator")
print("SmolVLM-500M + OCR")
print("="*80)

# Find all images
image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
image_files = []
for ext in image_extensions:
    image_files.extend(Path(TEST_FOLDER).glob(f"*{ext}"))
    image_files.extend(Path(TEST_FOLDER).glob(f"*{ext.upper()}"))

# Remove duplicates
image_files = list(set(image_files))

print(f"\nFound {len(image_files)} images in {TEST_FOLDER}")

if len(image_files) == 0:
    print("No images found! Exiting.")
    exit()

# Initialize OCR if available
ocr_reader = None
if OCR_AVAILABLE:
    print("\nInitializing EasyOCR for text detection...")
    ocr_reader = easyocr.Reader(['en'], gpu=True)
    print(">> OCR ready!")

# Load SmolVLM-500M
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

# Improved prompt - simpler and more focused
SIMPLE_PROMPT = """Describe what you see in this image. Include:
- Main subjects (people, vehicles, objects)
- Setting/location
- Colors and distinctive features
- Actions or activities
- Time of day if visible
Be specific and factual. Don't invent details."""

# Process images
results = []
total_time = 0

print(f"\nProcessing {len(image_files)} images...")
print("="*80)

for idx, image_path in enumerate(image_files, 1):
    try:
        # Load image
        image = Image.open(image_path).convert("RGB")
        
        # OCR text detection
        detected_text = []
        if ocr_reader:
            try:
                ocr_results = ocr_reader.readtext(str(image_path))
                detected_text = [text for (bbox, text, conf) in ocr_results if conf > 0.3]
            except:
                pass
        
        # Generate VLM description
        start = time.time()
        
        messages = [{
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": SIMPLE_PROMPT}
            ]
        }]
        
        prompt_text = processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = processor(text=prompt_text, images=[image], return_tensors="pt")
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=150, do_sample=False)
        
        generated_texts = processor.batch_decode(generated_ids, skip_special_tokens=True)
        description = generated_texts[0].split("Assistant:")[-1].strip()
        
        elapsed = time.time() - start
        total_time += elapsed
        
        # Combine description with OCR text
        full_description = description
        if detected_text:
            full_description += f"\n\nDetected text: {', '.join(detected_text)}"
        
        # Store result
        results.append({
            'filename': image_path.name,
            'path': str(image_path),
            'vlm_description': description,
            'detected_text': ', '.join(detected_text) if detected_text else '',
            'combined_description': full_description,
            'time_seconds': round(elapsed, 2)
        })
        
        # Print progress
        print(f"[{idx}/{len(image_files)}] {image_path.name}")
        print(f"  Time: {elapsed:.2f}s")
        if detected_text:
            print(f"  OCR Text: {', '.join(detected_text)}")
        print(f"  VLM: {description[:120]}{'...' if len(description) > 120 else ''}")
        print()
        
    except Exception as e:
        print(f"[{idx}/{len(image_files)}] ERROR processing {image_path.name}: {e}")
        results.append({
            'filename': image_path.name,
            'path': str(image_path),
            'vlm_description': f"ERROR: {str(e)}",
            'detected_text': '',
            'combined_description': f"ERROR: {str(e)}",
            'time_seconds': 0
        })

# Save to CSV
print("="*80)
print(f"\nSaving results to {OUTPUT_CSV}...")

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['filename', 'path', 'vlm_description', 'detected_text', 'combined_description', 'time_seconds'])
    writer.writeheader()
    writer.writerows(results)

print(f">> Results saved!")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total images processed: {len(results)}")
print(f"Successful: {sum(1 for r in results if not r['vlm_description'].startswith('ERROR'))}")
print(f"Failed: {sum(1 for r in results if r['vlm_description'].startswith('ERROR'))}")
if ocr_reader:
    print(f"Images with detected text: {sum(1 for r in results if r['detected_text'])}")
print(f"Total time: {total_time:.2f}s")
print(f"Average time per image: {total_time/len(results):.2f}s")
print(f"\nResults saved to: {OUTPUT_CSV}")
print("="*80 + "\n")
