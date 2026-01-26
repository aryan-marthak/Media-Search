"""
Test SmolVLM 2.2B model for Deep Search.
Compares performance and quality with the 500M model.
"""
import sys
import time
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForVision2Seq, BitsAndBytesConfig

def test_model(image_path: str, model_name: str, model_size: str):
    """Test a VLM model on a single image."""
    
    print(f"\n{'='*80}")
    print(f"Testing: {model_size}")
    print(f"Model: {model_name}")
    print(f"{'='*80}")
    
    # Load image
    print("\n1. Loading image...")
    image = Image.open(image_path).convert("RGB")
    
    # Resize to 512px
    max_size = 512
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    print(f"   Image size: {image.size}")
    
    # Load model with 4-bit quantization
    print("\n2. Loading model with 4-bit quantization...")
    start = time.time()
    
    config_4bit = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    )
    
    processor = AutoProcessor.from_pretrained(model_name)
    model = AutoModelForVision2Seq.from_pretrained(
        model_name,
        quantization_config=config_4bit,
        device_map="auto"
    )
    model.eval()
    
    load_time = time.time() - start
    print(f"   ✅ Model loaded in {load_time:.2f}s")
    
    # Generate description
    print("\n3. Generating description...")
    start = time.time()
    
    messages = [{
        "role": "user",
        "content": [
            {"type": "image"},
            {"type": "text", "text": "Describe this image in detail."}
        ]
    }]
    
    prompt_text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt_text, images=[image], return_tensors="pt")
    inputs = {k: v.to("cuda") for k, v in inputs.items()}
    
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=65,
            do_sample=False,
            num_beams=1,
            use_cache=True
        )
    
    generated_texts = processor.batch_decode(generated_ids, skip_special_tokens=True)
    caption = generated_texts[0].split("Assistant:")[-1].strip()
    
    generation_time = time.time() - start
    
    print(f"   ✅ Generated in {generation_time:.2f}s")
    print(f"\n📝 Description:")
    print(f"   {caption}")
    
    # Cleanup
    del model
    del processor
    torch.cuda.empty_cache()
    
    return {
        'model': model_size,
        'load_time': load_time,
        'generation_time': generation_time,
        'caption': caption,
        'caption_length': len(caption)
    }

def main(image_path: str):
    """Compare SmolVLM 500M vs 2.2B."""
    
    print("🔬 SmolVLM MODEL COMPARISON TEST")
    print("="*80)
    print(f"Image: {image_path}")
    
    results = []
    
    # Test 1: SmolVLM-Instruct (500M) - Current
    result1 = test_model(
        image_path,
        "HuggingFaceTB/SmolVLM-Instruct",
        "SmolVLM-Instruct (500M)"
    )
    results.append(result1)
    
    # Test 2: SmolVLM2-Instruct (2.2B) - New
    result2 = test_model(
        image_path,
        "HuggingFaceTB/SmolVLM2-Instruct",
        "SmolVLM2-Instruct (2.2B)"
    )
    results.append(result2)
    
    # Comparison
    print(f"\n{'='*80}")
    print("📊 COMPARISON RESULTS")
    print(f"{'='*80}")
    
    for result in results:
        print(f"\n{result['model']}:")
        print(f"  Load time: {result['load_time']:.2f}s")
        print(f"  Generation time: {result['generation_time']:.2f}s")
        print(f"  Caption length: {result['caption_length']} chars")
    
    # Speed difference
    speed_diff = result2['generation_time'] / result1['generation_time']
    print(f"\n⚡ Speed comparison:")
    print(f"  2.2B is {speed_diff:.2f}x {'slower' if speed_diff > 1 else 'faster'} than 500M")
    
    # Quality comparison
    print(f"\n📝 Quality comparison:")
    print(f"  500M: {result1['caption_length']} chars")
    print(f"  2.2B: {result2['caption_length']} chars")
    print(f"  Difference: {result2['caption_length'] - result1['caption_length']:+d} chars")
    
    print(f"\n{'='*80}")
    print("💡 RECOMMENDATION")
    print(f"{'='*80}")
    
    if speed_diff < 2 and result2['caption_length'] > result1['caption_length']:
        print("✅ SmolVLM2 (2.2B) is recommended!")
        print(f"   - Better quality (+{result2['caption_length'] - result1['caption_length']} chars)")
        print(f"   - Acceptable speed ({result2['generation_time']:.1f}s per image)")
    elif speed_diff > 3:
        print("⚠️  SmolVLM (500M) is recommended")
        print(f"   - Much faster ({result1['generation_time']:.1f}s vs {result2['generation_time']:.1f}s)")
        print(f"   - Quality difference may not justify the speed cost")
    else:
        print("🤔 Mixed results - depends on your priorities:")
        print(f"   - Choose 500M for speed ({result1['generation_time']:.1f}s)")
        print(f"   - Choose 2.2B for quality ({result2['caption_length']} chars)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_smolvlm_2b.py <path_to_image>")
        print("\nExample:")
        print('  python test_smolvlm_2b.py "D:\\gallery\\test\\20240209_184617.jpg"')
        sys.exit(1)
    
    main(sys.argv[1])
