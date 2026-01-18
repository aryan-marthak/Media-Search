"""
VLM Service for generating detailed image descriptions using SmolVLM.
Provides caption generation for Deep Search functionality.
"""
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForVision2Seq
from typing import Optional
import config

class VLMService:
    """Vision Language Model service for image captioning."""
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = config.DEVICE
        self._load_model()
    
    def _load_model(self):
        """Load SmolVLM-500M model with 4-bit quantization for 4GB GPU."""
        try:
            print(">> Loading SmolVLM-500M model with 4-bit quantization...")
            model_name = "HuggingFaceTB/SmolVLM-500M-Instruct"
            
            # Load processor with proper image size settings
            print(">> Downloading processor...")
            self.processor = AutoProcessor.from_pretrained(
                model_name,
                size={"longest_edge": 384},  # Optimized for 500M model
                do_image_splitting=False,
                resume_download=True
            )
            
            # Load model with 4-bit quantization for RTX 3050 (4GB VRAM)
            print(">> Downloading model weights with 4-bit quantization...")
            
            if self.device == "cuda":
                # Use 4-bit quantization to fit in 4GB VRAM
                from transformers import BitsAndBytesConfig
                
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16
                )
                
                self.model = AutoModelForVision2Seq.from_pretrained(
                    model_name,
                    quantization_config=quantization_config,
                    device_map="auto",
                    resume_download=True
                )
            else:
                # CPU fallback
                self.model = AutoModelForVision2Seq.from_pretrained(
                    model_name,
                    torch_dtype=torch.float32,
                    resume_download=True
                )
                self.model = self.model.to(self.device)
            
            self.model.eval()
            
            # Enable torch optimizations
            if self.device == "cuda":
                torch.backends.cudnn.benchmark = True
                vram_used = torch.cuda.memory_allocated() / 1024**3
                print(f">> ✅ SmolVLM-500M loaded successfully on {self.device}")
                print(f">> VRAM usage: {vram_used:.2f} GB / 4.00 GB")
            else:
                print(f">> ✅ SmolVLM-500M loaded successfully on {self.device}")
            
            print(">> Deep Search is now available!")
            
        except KeyboardInterrupt:
            print(">> ⚠️  VLM loading interrupted by user")
            print(">> Deep Search will be disabled")
            self.model = None
            self.processor = None
        except Exception as e:
            print(f">> ⚠️  Failed to load SmolVLM-500M: {str(e)}")
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
            
            # Generate caption
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=100,
                    do_sample=False
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
