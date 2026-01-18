from typing import Optional
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModel
import numpy as np

from config import SIGLIP_MODEL, DEVICE, SIGLIP_EMBEDDING_DIM

# Global model cache
_model = None
_processor = None
_actual_device = None


def get_device():
    """Get the actual device to use (with CUDA fallback to CPU)."""
    global _actual_device
    if _actual_device is None:
        if DEVICE == "cuda":
            try:
                if torch.cuda.is_available():
                    _actual_device = "cuda"
                    print(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
                else:
                    _actual_device = "cpu"
                    print("⚠️ CUDA not available, using CPU")
            except Exception as e:
                _actual_device = "cpu"
                print(f"⚠️ CUDA initialization failed ({e}), using CPU")
        else:
            _actual_device = "cpu"
    return _actual_device


def get_siglip_model():
    """Get or initialize the SigLIP model (singleton)."""
    global _model, _processor
    
    if _model is None:
        device = get_device()
        print(f"🔄 Loading SigLIP model: {SIGLIP_MODEL}")
        try:
            _processor = AutoProcessor.from_pretrained(SIGLIP_MODEL)
            _model = AutoModel.from_pretrained(SIGLIP_MODEL)
            _model.to(device)
            _model.eval()
            print(f"✅ SigLIP model loaded on {device}")
        except Exception as e:
            print(f"❌ Failed to load SigLIP model: {e}")
            raise
    
    return _model, _processor


def encode_image(image: Image.Image) -> np.ndarray:
    """
    Encode an image to a SigLIP embedding vector.
    
    Args:
        image: PIL Image
        
    Returns:
        768-dimensional embedding vector
    """
    model, processor = get_siglip_model()
    device = get_device()
    
    # Preprocess image
    inputs = processor(images=image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    # Generate embedding
    with torch.no_grad():
        outputs = model.get_image_features(**inputs)
        embedding = outputs.cpu().numpy().flatten()
    
    # Clear GPU memory to prevent OOM on low VRAM GPUs
    if device == "cuda":
        del inputs, outputs
        torch.cuda.empty_cache()
    
    # Normalize
    embedding = embedding / np.linalg.norm(embedding)
    
    return embedding


def encode_text(text: str) -> np.ndarray:
    """
    Encode text to a SigLIP embedding vector.
    
    Args:
        text: Query string
        
    Returns:
        768-dimensional embedding vector
    """
    model, processor = get_siglip_model()
    device = get_device()
    
    # Preprocess text
    inputs = processor(text=[text], return_tensors="pt", padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    # Generate embedding
    with torch.no_grad():
        outputs = model.get_text_features(**inputs)
        embedding = outputs.cpu().numpy().flatten()
    
    # Normalize
    embedding = embedding / np.linalg.norm(embedding)
    
    return embedding


def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings."""
    return float(np.dot(embedding1, embedding2))


def sigmoid(x: float) -> float:
    """Sigmoid function for score calibration."""
    import math
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 1.0 if x > 0 else 0.0


def calibrate_siglip_score(raw_similarity: float, temperature: float = 25.0) -> float:
    """
    Calibrate raw SigLIP cosine similarity to a meaningful confidence score.
    
    SigLIP uses a learned temperature parameter during training. This applies
    a similar calibration to convert raw cosine similarities to confidence scores.
    
    Args:
        raw_similarity: Cosine similarity from -1 to 1
        temperature: Temperature parameter (default 25 from SigLIP paper)
        
    Returns:
        Calibrated score from 0 to 1
    """
    # Scale by temperature and apply sigmoid
    scaled = raw_similarity * temperature
    return sigmoid(scaled)
