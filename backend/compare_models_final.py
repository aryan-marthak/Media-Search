"""
Final comparison: SmolVLM 500M vs SmolVLM2 2.2B
Shows complete descriptions side-by-side.
"""
import sys
from PIL import Image
import torch
from transformers import AutoProcessor, Idefics3ForConditionalGeneration, BitsAndBytesConfig
import time

def test_both_models(image_path: str):
    """Test both models and compare results."""
    
    print("🔬 SMOLVLM FINAL COMPARISON")
    print("="*80)
    
    image = Image.open(image_path).convert("RGB")
    max_size = 512
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    config_4bit = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    )
    
    results = []
    
    # Test SmolVLM 500M
    print("\n📊 Testing SmolVLM-Instruct (500M)...")
    model_name = "HuggingFaceTB/SmolVLM-Instruct"
    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    model = Idefics3ForConditionalGeneration.from_pretrained(
        model_name, quantization_config=config_4bit, device_map="auto", trust_remote_code=True
    )
    
    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": "Describe this image in detail."}]}]
    prompt_text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt_text, images=[image], return_tensors="pt")
    inputs = {k: v.to("cuda") for k, v in inputs.items()}
    
    start = time.time()
    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=150, do_sample=False, use_cache=True)
    gen_time_500m = time.time() - start
    
    caption_500m = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].split("Assistant:")[-1].strip()
    
    del model, processor
    torch.cuda.empty_cache()
    
    # Test SmolVLM2 2.2B
    print("📊 Testing SmolVLM2-Instruct (2.2B)...")
    model_name = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"
    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    model = Idefics3ForConditionalGeneration.from_pretrained(
        model_name, quantization_config=config_4bit, device_map="auto", trust_remote_code=True
    )
    
    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": "Describe this image in detail."}]}]
    prompt_text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt_text, images=[image], return_tensors="pt")
    inputs = {k: v.to("cuda") for k, v in inputs.items()}
    
    start = time.time()
    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=150, do_sample=False, use_cache=True)
    gen_time_2b = time.time() - start
    
    caption_2b = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].split("Assistant:")[-1].strip()
    
    # Results
    print("\n" + "="*80)
    print("📊 COMPARISON RESULTS")
    print("="*80)
    
    print(f"\n🔹 SmolVLM 500M:")
    print(f"   Time: {gen_time_500m:.2f}s")
    print(f"   Length: {len(caption_500m)} chars")
    print(f"   Description:\n   {caption_500m}\n")
    
    print(f"🔹 SmolVLM2 2.2B:")
    print(f"   Time: {gen_time_2b:.2f}s")
    print(f"   Length: {len(caption_2b)} chars")
    print(f"   Description:\n   {caption_2b}\n")
    
    print("="*80)
    print("💡 RECOMMENDATION")
    print("="*80)
    print(f"SmolVLM2 (2.2B) is {len(caption_2b)/len(caption_500m):.1f}x more detailed")
    print(f"Speed difference: {gen_time_2b - gen_time_500m:+.2f}s ({abs((gen_time_2b/gen_time_500m - 1)*100):.0f}% {'slower' if gen_time_2b > gen_time_500m else 'faster'})")
    print(f"\n✅ Use SmolVLM2-2.2B for better Deep Search quality!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python compare_models_final.py "D:\\gallery\\test\\image.jpg"')
        sys.exit(1)
    test_both_models(sys.argv[1])
