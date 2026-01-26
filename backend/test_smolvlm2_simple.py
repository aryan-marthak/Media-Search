"""
Simple test for SmolVLM 2.2B model.
Tests just the 2.2B model to see if it works.
"""
import sys
import time
from PIL import Image
import torch
from transformers import AutoProcessor, Idefics3ForConditionalGeneration, BitsAndBytesConfig

def test_smolvlm2(image_path: str):
    """Test SmolVLM2 (2.2B) model."""
    
    print("🔬 Testing SmolVLM2-Instruct (2.2B)")
    print("="*80)
    
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
    print("\n2. Loading SmolVLM2 model with 4-bit quantization...")
    start = time.time()
    
    model_name = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"  # Correct model name
    
    config_4bit = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    )
    
    try:
        processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
        model = Idefics3ForConditionalGeneration.from_pretrained(
            model_name,
            quantization_config=config_4bit,
            device_map="auto",
            trust_remote_code=True
        )
        model.eval()
        
        load_time = time.time() - start
        print(f"   ✅ Model loaded in {load_time:.2f}s")
        
    except Exception as e:
        print(f"   ❌ Failed to load model: {str(e)}")
        print("\n💡 Trying alternative: SmolVLM-256M-Instruct (smaller, faster)")
        return
    
    # Generate description
    print("\n3. Generating description...")
    start = time.time()
    
    # Prepare prompt
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": "Describe this image in detail."}
            ]
        }
    ]
    
    prompt_text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt_text, images=[image], return_tensors="pt")
    inputs = {k: v.to("cuda") for k, v in inputs.items()}
    
    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=150,  # Increased for 2.2B model's detailed descriptions
            do_sample=False,
            use_cache=True
        )
    
    generated_texts = processor.batch_decode(generated_ids, skip_special_tokens=True)
    caption = generated_texts[0].split("Assistant:")[-1].strip()
    
    generation_time = time.time() - start
    
    print(f"   ✅ Generated in {generation_time:.2f}s")
    print(f"\n📝 Description:")
    print(f"   {caption}")
    
    print(f"\n{'='*80}")
    print("📊 RESULTS")
    print(f"{'='*80}")
    print(f"Model: SmolVLM2-Instruct (2.2B)")
    print(f"Load time: {load_time:.2f}s")
    print(f"Generation time: {generation_time:.2f}s")
    print(f"Caption length: {len(caption)} chars")
    print(f"\n💡 For 100 images: ~{generation_time * 100 / 60:.1f} minutes")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_smolvlm2_simple.py <path_to_image>")
        print("\nExample:")
        print('  python test_smolvlm2_simple.py "D:\\gallery\\test\\20240209_184617.jpg"')
        sys.exit(1)
    
    test_smolvlm2(sys.argv[1])
