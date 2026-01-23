"""
Deep Search Metadata Generator - SmolVLM-500M Test Script

Generates detailed metadata descriptions for images to enable deep search functionality.
Processes a folder of images and creates searchable descriptions.

Usage:
    python test_deep_search.py <folder_path>
    
Example:
    python test_deep_search.py "D:\gallery\test"
"""

import os
import sys
import time
import csv
from pathlib import Path
from datetime import datetime
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForVision2Seq, BitsAndBytesConfig

# Configuration
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.heic']

def print_header():
    """Print script header"""
    print("\n" + "="*80)
    print("Deep Search Metadata Generator")
    print("SmolVLM-500M-Instruct (4-bit quantized)")
    print("="*80 + "\n")

def find_images(folder_path):
    """Find all images in the specified folder"""
    image_files = []
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"❌ Error: Folder '{folder_path}' does not exist!")
        sys.exit(1)
    
    for ext in IMAGE_EXTENSIONS:
        image_files.extend(folder.glob(f"*{ext}"))
        image_files.extend(folder.glob(f"*{ext.upper()}"))
    
    # Remove duplicates and sort
    image_files = sorted(list(set(image_files)))
    
    return image_files

def load_model():
    """Load SmolVLM-500M model with 4-bit quantization"""
    print("📦 Loading SmolVLM-500M model...")
    
    model_name = "HuggingFaceTB/SmolVLM-500M-Instruct"
    
    # Load processor
    processor = AutoProcessor.from_pretrained(
        model_name,
        size={"longest_edge": 384},
        do_image_splitting=False
    )
    
    # Try to load with 4-bit quantization, fall back if not available
    try:
        print("   - Attempting 4-bit quantization for efficiency")
        print("   - Device: GPU (CUDA)")
        
        from transformers import BitsAndBytesConfig
        
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16
        )
        
        model = AutoModelForVision2Seq.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto"
        )
        print("   ✅ Using 4-bit quantization")
        
    except Exception as e:
        print(f"   ⚠️  4-bit quantization not available: {str(e)[:50]}")
        print("   - Loading model in float16 instead")
        print("   - Device: GPU (CUDA)")
        
        model = AutoModelForVision2Seq.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        print("   ✅ Using float16 precision")
    
    model.eval()
    
    # Check VRAM usage
    if torch.cuda.is_available():
        vram_used = torch.cuda.memory_allocated() / 1024**3
        vram_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"   📊 VRAM: {vram_used:.2f} GB / {vram_total:.2f} GB")
    
    print("✅ Model loaded successfully!\n")
    
    return processor, model

def generate_description(image_path, processor, model):
    """Generate detailed metadata description for an image"""
    
    # Deep search optimized prompt
    DEEP_SEARCH_PROMPT = """Describe this image in detail for search purposes. Include:

1. Main subjects: What/who is the primary focus?
2. Objects & items: List all visible objects, items, or elements
3. Setting & location: Where is this? Indoor/outdoor? Type of place?
4. Colors & appearance: Dominant colors, visual style, patterns
5. Actions & activities: What's happening? Any movement or activity?
6. Text & signs: Any visible text, signs, labels, or writing
7. Time & lighting: Time of day? Lighting conditions?
8. Distinctive features: Unique or notable details that stand out

Be specific, factual, and detailed. Only describe what you actually see."""

    # Load and process image
    image = Image.open(image_path).convert("RGB")
    
    # Create messages
    messages = [{
        "role": "user",
        "content": [
            {"type": "image"},
            {"type": "text", "text": DEEP_SEARCH_PROMPT}
        ]
    }]
    
    # Process with model
    prompt_text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt_text, images=[image], return_tensors="pt")
    inputs = {k: v.to("cuda") for k, v in inputs.items()}
    
    # Generate description
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs, 
            max_new_tokens=200,  # Allow detailed descriptions
            do_sample=False
        )
    
    # Decode output
    generated_texts = processor.batch_decode(generated_ids, skip_special_tokens=True)
    description = generated_texts[0].split("Assistant:")[-1].strip()
    
    return description

def process_images(folder_path):
    """Process all images in the folder"""
    
    print_header()
    
    # Find images
    print(f"📁 Scanning folder: {folder_path}")
    image_files = find_images(folder_path)
    
    if len(image_files) == 0:
        print(f"❌ No images found in '{folder_path}'")
        print(f"   Supported formats: {', '.join(IMAGE_EXTENSIONS)}")
        sys.exit(1)
    
    print(f"✅ Found {len(image_files)} images\n")
    
    # Load model
    processor, model = load_model()
    
    # Prepare output
    output_csv = Path(folder_path) / f"deep_search_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    results = []
    total_time = 0
    
    # Process each image
    print("🔄 Processing images...")
    print("="*80 + "\n")
    
    for idx, image_path in enumerate(image_files, 1):
        try:
            start_time = time.time()
            
            # Generate description
            description = generate_description(image_path, processor, model)
            
            elapsed = time.time() - start_time
            total_time += elapsed
            
            # Store result
            result = {
                'filename': image_path.name,
                'path': str(image_path),
                'description': description,
                'time_seconds': round(elapsed, 2)
            }
            results.append(result)
            
            # Print progress
            print(f"[{idx}/{len(image_files)}] {image_path.name}")
            print(f"   ⏱️  Time: {elapsed:.2f}s")
            print(f"   📝 Description: {description[:150]}{'...' if len(description) > 150 else ''}")
            print()
            
        except Exception as e:
            print(f"[{idx}/{len(image_files)}] ❌ ERROR: {image_path.name}")
            print(f"   {str(e)}")
            print()
            
            results.append({
                'filename': image_path.name,
                'path': str(image_path),
                'description': f"ERROR: {str(e)}",
                'time_seconds': 0
            })
    
    # Save results
    print("="*80)
    print(f"\n💾 Saving results to CSV...")
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['filename', 'path', 'description', 'time_seconds'])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"✅ Results saved to: {output_csv.name}\n")
    
    # Print summary
    print("="*80)
    print("📊 SUMMARY")
    print("="*80)
    successful = sum(1 for r in results if not r['description'].startswith('ERROR'))
    failed = sum(1 for r in results if r['description'].startswith('ERROR'))
    
    print(f"Total images processed: {len(results)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Total time: {total_time:.2f}s")
    print(f"⚡ Average time per image: {total_time/len(results):.2f}s")
    print(f"\n📄 Results file: {output_csv}")
    print("="*80 + "\n")

def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("\n❌ Error: Please provide a folder path")
        print("\nUsage:")
        print('    python test_deep_search.py "D:\\gallery\\test"')
        print('    python test_deep_search.py "C:\\Users\\YourName\\Pictures\\TestFolder"')
        sys.exit(1)
    
    folder_path = sys.argv[1]
    process_images(folder_path)

if __name__ == "__main__":
    main()
