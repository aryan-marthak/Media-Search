"""
Face detection and recognition service using DeepFace with ArcFace.
"""
import os
import time
from pathlib import Path
from typing import List, Dict
import numpy as np
from PIL import Image
from deepface import DeepFace
import cv2

import config

# Configure TensorFlow to use GPU if available
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
import tensorflow as tf

# Enable GPU memory growth to avoid OOM errors
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f">> TensorFlow GPU enabled: {len(gpus)} GPU(s) available")
    except RuntimeError as e:
        print(f">> TensorFlow GPU configuration error: {e}")


class FaceService:
    """Service for face detection and embedding extraction using ArcFace."""
    
    def __init__(self):
        """Initialize DeepFace with ArcFace model."""
        self.model_name = "ArcFace"  # Best accuracy for face clustering
        self.detector_backend = "retinaface"  # More accurate detector (catches small/side faces)
        self.face_storage = Path(config.STORAGE_DIR) / "faces"
        self.face_storage.mkdir(parents=True, exist_ok=True)
        
        print(f">> Preloading {self.model_name} model and {self.detector_backend} detector...")
        
        # Preload models to avoid lazy loading on first use
        try:
            # Explicitly build the recognition model
            DeepFace.build_model(self.model_name)
            
            # Create a test image to trigger detector initialization
            test_img = np.ones((200, 200, 3), dtype=np.uint8) * 128
            test_img[50:150, 75:125] = 180  # Lighter "face" region
            
            # Run face detection to trigger full initialization
            _ = DeepFace.represent(
                img_path=test_img,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                align=True
            )
            
            print(f">> Face Service ready with {self.model_name} model and {self.detector_backend} detector")
        except Exception as e:
            print(f">> Warning: Could not preload face models: {str(e)}")
            print(f">> Models will be loaded on first use")
    
    def detect_and_extract_faces(self, image: Image.Image) -> List[Dict]:
        """
        Detect faces in image and extract embeddings using ArcFace.
        
        Args:
            image: PIL Image
            
        Returns:
            List of face dictionaries containing:
                - embedding: 512-dim numpy array
                - bbox: (x, y, width, height)
                - confidence: detection confidence
                - face_crop: PIL Image of face
        """
        start_time = time.time()
        try:
            # Convert PIL to numpy array (RGB)
            img_array = np.array(image)
            
            # DeepFace expects BGR for cv2
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # Detect faces and extract embeddings
            face_objs = DeepFace.represent(
                img_path=img_bgr,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False,  # Don't fail if no faces found
                align=True
            )
            
            faces = []
            for face_obj in face_objs:
                # Extract bounding box
                facial_area = face_obj.get("facial_area", {})
                x = facial_area.get("x", 0)
                y = facial_area.get("y", 0)
                w = facial_area.get("w", 0)
                h = facial_area.get("h", 0)
                
                # Skip invalid detections
                if w == 0 or h == 0:
                    continue
                
                # Extract face crop
                face_crop = image.crop((x, y, x + w, y + h))
                
                # Get embedding (512-dim for ArcFace)
                embedding = np.array(face_obj["embedding"])
                
                # Normalize embedding (L2 normalization)
                embedding = embedding / np.linalg.norm(embedding)
                
                # Get confidence
                confidence = face_obj.get("confidence", 1.0)
                
                faces.append({
                    "embedding": embedding,
                    "bbox": (x, y, w, h),
                    "confidence": confidence,
                    "face_crop": face_crop
                })
            
            elapsed = time.time() - start_time
            print(f">> Detected {len(faces)} face(s) in {elapsed:.2f}s")
            return faces
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f">> Face detection error after {elapsed:.2f}s: {str(e)}")
            return []
    
    def save_face_thumbnail(self, face_crop: Image.Image, face_id: str) -> str:
        """
        Save face crop as thumbnail.
        
        Args:
            face_crop: PIL Image of face
            face_id: UUID of face
            
        Returns:
            Path to saved thumbnail
        """
        # Resize to 100x100 for consistency
        thumbnail = face_crop.resize((100, 100), Image.Resampling.LANCZOS)
        
        # Save as JPEG
        thumbnail_path = self.face_storage / f"{face_id}.jpg"
        thumbnail.save(thumbnail_path, "JPEG", quality=90)
        
        return str(thumbnail_path)
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two face embeddings.
        
        Args:
            embedding1: First embedding (normalized)
            embedding2: Second embedding (normalized)
            
        Returns:
            Similarity score (0-1, higher is more similar)
        """
        # Cosine similarity (embeddings are already normalized)
        similarity = np.dot(embedding1, embedding2)
        
        return float(similarity)


# Singleton instance
_face_service = None


def get_face_service() -> FaceService:
    """Get or create FaceService singleton."""
    global _face_service
    if _face_service is None:
        _face_service = FaceService()
    return _face_service
