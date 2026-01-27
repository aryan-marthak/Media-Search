"""
VLM Service for generating detailed image descriptions using SmolVLM2 (2.2B).
Provides caption generation for Deep Search functionality.
Optimized with 4-bit quantization for fast inference (~5-6 seconds per image).
"""
from PIL import Image
import torch
from transformers import AutoProcessor, Idefics3ForConditionalGeneration, BitsAndBytesConfig
from typing import Optional
import config

class VLMService:
    """Vision Language Model service for image captioning using SmolVLM2 (2.2B)."""
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = config.DEVICE
        if config.ENABLE_VLM:
            self._load_model()
    
    def _load_model(self):
        """Load SmolVLM2 (2.2B) model with 4-bit quantization."""
        try:
            print(">> Loading SmolVLM2-2.2B model with 4-bit quantization...")
            model_name = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"
            
            # 4-bit quantization config for fast inference
            config_4bit = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
            
            # Load processor
            print(">> Downloading processor...")
            self.processor = AutoProcessor.from_pretrained(
                model_name,
                trust_remote_code=True
            )
            
            # Load model with 4-bit quantization
            print(">> Downloading model weights (first run may take 5-10 minutes)...")
            self.model = Idefics3ForConditionalGeneration.from_pretrained(
                model_name,
                quantization_config=config_4bit,
                device_map="auto",
                trust_remote_code=True
            )
            
            self.model.eval()
            
            print(f">> ✅ SmolVLM2-2.2B loaded successfully on {self.device} (4-bit optimized)")
            print(">> Deep Search is now available!")
            print(">> Performance: ~5-6 seconds per image, 100 images in ~9-10 minutes")
            
        except KeyboardInterrupt:
            print(">> ⚠️  VLM loading interrupted by user")
            print(">> Deep Search will be disabled")
            self.model = None
            self.processor = None
        except Exception as e:
            print(f">> ⚠️  Failed to load SmolVLM2: {str(e)}")
            print(">> Deep Search will be disabled - uploads will continue normally")
            self.model = None
            self.processor = None
    
    def generate_caption(self, image: Image.Image, prompt: str = "Describe this image in detail.") -> Optional[str]:
        """
        Generate a detailed caption for an image.
        
        Args:
            image: PIL Image object
            prompt: Text prompt for caption generation
            
        Returns:
            Generated caption string, or None if model not loaded
        """
        if self.model is None or self.processor is None:
            return None
        
        try:
            # Resize large images for faster processing
            max_size = 512
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Prepare inputs
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            # Apply chat template
            prompt_text = self.processor.apply_chat_template(
                messages, 
                add_generation_prompt=True
            )
            
            # Process inputs
            inputs = self.processor(
                text=prompt_text,
                images=[image],
                return_tensors="pt"
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate caption with optimizations
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=150,  # Enough for detailed descriptions
                    do_sample=False,
                    use_cache=True
                )
            
            # Decode output
            generated_texts = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )
            
            # Extract assistant response
            caption = generated_texts[0].split("Assistant:")[-1].strip()
            
            return caption
            
        except Exception as e:
            print(f">> ⚠️  Caption generation failed: {str(e)}")
            return None
    
    def is_available(self) -> bool:
        """Check if VLM service is available."""
        return self.model is not None and self.processor is not None


# Singleton instance
_vlm_service = None

def get_vlm_service() -> VLMService:
    """Get or create VLM service singleton."""
    global _vlm_service
    if _vlm_service is None:
        _vlm_service = VLMService()
    return _vlm_service
