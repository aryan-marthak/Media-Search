"""Quick test of SmolVLM on an actual image."""
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq
import time

# Use a smaller image for the test
img_path = r"D:\Media-Search\data\images\54e0720a-dbca-40a5-b5c2-297d2f0ad05a\2aec6c26-f74d-49ed-8107-6d5151526c7d.jpg"
print(f"Loading image: {img_path}")
img = Image.open(img_path).convert('RGB')
print(f"Image size: {img.size}")

# Resize if too large to save VRAM
if img.size[0] > 512 or img.size[1] > 512:
    img.thumbnail((512, 512))
    print(f"Resized to: {img.size}")

print("\nLoading SmolVLM model...")
start = time.time()
processor = AutoProcessor.from_pretrained('HuggingFaceTB/SmolVLM-Instruct')
model = AutoModelForVision2Seq.from_pretrained(
    'HuggingFaceTB/SmolVLM-Instruct', 
    torch_dtype=torch.float16, 
    device_map='cuda'
)
print(f"Model loaded in {time.time()-start:.1f}s")

# Simple test prompt - NO example in the prompt
prompt_text = "Describe what you see in this image in one sentence."
messages = [
    {
        'role': 'user', 
        'content': [
            {'type': 'image'}, 
            {'type': 'text', 'text': prompt_text}
        ]
    }
]

print(f"\nPrompt: {prompt_text}")
print("\nGenerating...")
start = time.time()

prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
inputs = processor(text=prompt, images=[img], return_tensors='pt').to('cuda')

with torch.no_grad():
    out = model.generate(**inputs, max_new_tokens=100, do_sample=False)
    
output = processor.decode(out[0], skip_special_tokens=True)
print(f"\nGeneration took: {time.time()-start:.1f}s")
print(f"\n=== VLM OUTPUT ===")
print(output)
print("==================")
