from typing import Dict, Optional
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq
import json
import re

from config import VLM_MODEL, DEVICE

# Global model cache
_model = None
_processor = None


def get_vlm_model():
    """Get or initialize the VLM model (singleton)."""
    global _model, _processor
    
    if _model is None:
        print(f"🔄 Loading VLM model: {VLM_MODEL}")
        _processor = AutoProcessor.from_pretrained(VLM_MODEL)
        _model = AutoModelForVision2Seq.from_pretrained(
            VLM_MODEL,
            torch_dtype=torch.float16,
            device_map=DEVICE
        )
        print(f"✅ VLM model loaded on {DEVICE}")
    
    return _model, _processor


METADATA_PROMPT = """Analyze this image and extract structured metadata. Return a JSON object with these fields:
- objects: list of main objects/subjects (e.g. ["person", "car", "dog"])
- action: primary action happening (e.g. "walking", "sitting", "running")
- time: time of day if visible (e.g. "day", "night", "sunset", "dawn")
- scene: type of scene/location (e.g. "street", "beach", "indoor", "park")
- weather: weather if outdoor (e.g. "sunny", "rainy", "cloudy") or null
- emotion: visible emotion if people present (e.g. "happy", "sad") or null
- caption: brief natural language description

Return ONLY valid JSON, no other text.
Example: {"objects": ["person"], "action": "walking", "time": "night", "scene": "street", "weather": null, "emotion": null, "caption": "A person walking on a street at night"}"""


def extract_metadata(image: Image.Image) -> Dict[str, any]:
    """
    Extract structured metadata from an image using VLM.
    
    Args:
        image: PIL Image
        
    Returns:
        Dictionary with objects, action, time, scene, weather, emotion, caption
    """
    model, processor = get_vlm_model()
    
    # Prepare input
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": METADATA_PROMPT}
            ]
        }
    ]
    
    prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt, images=[image], return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False
        )
    
    # Decode response
    response = processor.decode(outputs[0], skip_special_tokens=True)
    
    # Extract JSON from response
    metadata = parse_metadata_response(response)
    
    return metadata


def parse_metadata_response(response: str) -> Dict[str, any]:
    """Parse VLM response to extract JSON metadata."""
    # Default metadata
    default = {
        "objects": [],
        "action": None,
        "time": None,
        "scene": None,
        "weather": None,
        "emotion": None,
        "caption": None
    }
    
    try:
        # Find JSON in response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            metadata = json.loads(json_match.group())
            # Validate and fill missing fields
            for key in default:
                if key not in metadata:
                    metadata[key] = default[key]
            return metadata
    except (json.JSONDecodeError, Exception):
        pass
    
    return default


def validate_image_for_query(image: Image.Image, query: str) -> tuple[bool, float, str]:
    """
    Use VLM to validate if an image matches a query.
    Used in deep search for final validation.
    
    Returns:
        (matches: bool, confidence: float, explanation: str)
    """
    model, processor = get_vlm_model()
    
    validation_prompt = f"""Does this image match the query: "{query}"?

Answer with:
- MATCH: yes or no
- CONFIDENCE: 0.0 to 1.0
- REASON: brief explanation

Format your response exactly like:
MATCH: yes
CONFIDENCE: 0.85
REASON: The image shows a person walking on a street at night."""

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": validation_prompt}
            ]
        }
    ]
    
    prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt, images=[image], return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=100,
            do_sample=False
        )
    
    response = processor.decode(outputs[0], skip_special_tokens=True)
    
    # Parse response
    matches = "yes" in response.lower().split("match:")[-1].split("\n")[0].lower()
    
    confidence = 0.5
    if "confidence:" in response.lower():
        try:
            conf_str = response.lower().split("confidence:")[-1].split("\n")[0].strip()
            confidence = float(re.search(r'[\d.]+', conf_str).group())
        except:
            pass
    
    reason = ""
    if "reason:" in response.lower():
        reason = response.split("REASON:")[-1].strip() if "REASON:" in response else ""
    
    return matches, confidence, reason
