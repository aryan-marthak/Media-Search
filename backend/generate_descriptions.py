"""
Generate semantic search descriptions for images using SmolVLM-2.2B-Instruct
Usage: python generate_descriptions.py <image_path_or_folder>
"""

import os
import sys
import time
from pathlib import Path
from PIL import Image
import torch
from transformers import AutoProcessor
from transformers.models.smolvlm import SmolVLMForConditionalGeneration

# Configuration
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.heic']
MODEL_NAME = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"

# Prompt for factual, concise descriptions
PROMPT = """Describe this Image"""


class ImageDescriptionGenerator:
    def __init__(self):
        self.processor = None
        self.model = None
        
    def load_model(self):
        """Load SmolVLM-2.2B model"""
        if self.model is not None:
            return
            
        print("Loading SmolVLM-2.2B model (4-bit)...")
        
        # Load processor
        self.processor = AutoProcessor.from_pretrained(
            MODEL_NAME,
            size={"longest_edge": 512},
            do_image_splitting=False
        )
        
        # Load model with 4-bit quantization
        self.model = SmolVLMForConditionalGeneration.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )
        print("✓ Model loaded with float16")
        
        
        self.model.eval()
        
        # Show VRAM usage
        if torch.cuda.is_available():
            vram_used = torch.cuda.memory_allocated() / 1024**3
            vram_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"✓ VRAM: {vram_used:.2f} GB / {vram_total:.2f} GB\n")
    
    def generate_description(self, image_path):
        """Generate description for a single image"""
        if self.model is None:
            self.load_model()
        
        # Load and process image
        image = Image.open(image_path).convert("RGB")
        
        # Create messages
        messages = [{
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": PROMPT}
            ]
        }]
        
        # Process with model
        prompt_text = self.processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = self.processor(text=prompt_text, images=[image], return_tensors="pt")
        
        # Generate description
        with torch.no_grad():
            generated_ids = self.model.generate(
            **inputs,
            max_new_tokens=140,
            do_sample=True,
            temperature=0.3,
            top_p=0.9,
            repetition_penalty=1.05,
            eos_token_id=self.processor.tokenizer.eos_token_id,
            pad_token_id=self.processor.tokenizer.pad_token_id
        )



        
        # Decode output
        generated_texts = self.processor.batch_decode(generated_ids, skip_special_tokens=True)
        description = generated_texts[0].split("Assistant:")[-1].strip()
        
        return description


def find_images(path):
    """Find all images in path (file or folder)"""
    path = Path(path)
    
    if not path.exists():
        print(f"Error: Path '{path}' does not exist!")
        sys.exit(1)
    
    if path.is_file():
        if path.suffix.lower() in IMAGE_EXTENSIONS:
            return [path]
        else:
            print(f"Error: '{path}' is not a supported image format")
            sys.exit(1)
    
    # Find all images in folder
    image_files = []
    for ext in IMAGE_EXTENSIONS:
        image_files.extend(path.glob(f"*{ext}"))
        image_files.extend(path.glob(f"*{ext.upper()}"))
    
    return sorted(list(set(image_files)))


def main():
    if len(sys.argv) != 2:
        print("\nUsage:")
        print('  python generate_descriptions.py <image_path>')
        print('  python generate_descriptions.py <folder_path>')
        print('\nExamples:')
        print('  python generate_descriptions.py "D:\\gallery\\photo.jpg"')
        print('  python generate_descriptions.py "D:\\gallery\\photos"')
        sys.exit(1)
    
    input_path = sys.argv[1]
    image_files = find_images(input_path)
    
    if len(image_files) == 0:
        print(f"No images found in '{input_path}'")
        print(f"Supported formats: {', '.join(IMAGE_EXTENSIONS)}")
        sys.exit(1)
    
    print(f"Found {len(image_files)} image(s)\n")
    
    # Initialize generator
    generator = ImageDescriptionGenerator()
    
    # Process images
    for idx, image_path in enumerate(image_files, 1):
        try:
            print(f"[{idx}/{len(image_files)}] {image_path.name}")
            start_time = time.time()
            
            description = generator.generate_description(image_path)
            
            elapsed = time.time() - start_time
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Description: {description}\n")
            
        except Exception as e:
            print(f"  ERROR: {str(e)}\n")


if __name__ == "__main__":
    main()
