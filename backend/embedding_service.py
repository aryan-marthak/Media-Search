"""
CLIP embedding service for text and image encoding.
Provides advanced features like local re-ranking and zero-shot classification.
"""
import torch
import open_clip
from PIL import Image
import numpy as np
import config


class CLIPEmbeddingService:
    """CLIP ViT-L/14 embedding service for text and images."""
    
    def __init__(self):
        """Initialize CLIP model."""
        print(f"Loading CLIP model: {config.CLIP_MODEL} ({config.CLIP_PRETRAINED})")
        
        self.device = config.DEVICE
        
        # Load CLIP model
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            config.CLIP_MODEL,
            pretrained=config.CLIP_PRETRAINED,
            device=self.device
        )
        
        self.tokenizer = open_clip.get_tokenizer(config.CLIP_MODEL)
        self.model.eval()
        
        print(f">> CLIP model loaded on {self.device}")
    
    def encode_text(self, text: str) -> np.ndarray:
        """
        Encode text query to embedding.
        
        Args:
            text: Text query to encode
            
        Returns:
            Normalized embedding vector (768-dim)
        """
        with torch.no_grad():
            # Tokenize text
            text_tokens = self.tokenizer([text]).to(self.device)
            
            # Get text features
            text_features = self.model.encode_text(text_tokens)
            
            # Normalize
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            
            return text_features.cpu().numpy()[0]
    
    def encode_image(self, image: Image.Image) -> np.ndarray:
        """
        Encode image to embedding.
        
        Args:
            image: PIL Image to encode
            
        Returns:
            Normalized embedding vector (768-dim)
        """
        with torch.no_grad():
            # Preprocess image
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # Get image features
            image_features = self.model.encode_image(image_input)
            
            # Normalize
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy()[0]
    
    def compute_similarity(self, text_embedding: np.ndarray, image_embedding: np.ndarray) -> float:
        """
        Compute cosine similarity between text and image embeddings.
        
        Args:
            text_embedding: Text embedding vector
            image_embedding: Image embedding vector
            
        Returns:
            Cosine similarity score (higher is better)
        """
        similarity = np.dot(text_embedding, image_embedding)
        return float(similarity)
    
    def generate_crops(self, image: Image.Image, num_crops: int = 5) -> list:
        """
        Generate crops from image for local re-ranking.
        
        Args:
            image: PIL Image to crop
            num_crops: Number of crops to generate
            
        Returns:
            List of cropped PIL Images
        """
        width, height = image.size
        crops = []
        
        # Center crop
        crop_size = min(width, height)
        left = (width - crop_size) // 2
        top = (height - crop_size) // 2
        center_crop = image.crop((left, top, left + crop_size, top + crop_size))
        crops.append(center_crop)
        
        # 2x2 grid crops
        crop_w = width // 2
        crop_h = height // 2
        
        for i in range(2):
            for j in range(2):
                left = j * crop_w
                top = i * crop_h
                crop = image.crop((left, top, left + crop_w, top + crop_h))
                crops.append(crop)
        
        return crops[:num_crops]
    
    def encode_image_local(self, image: Image.Image) -> list:
        """
        Encode image crops to embeddings.
        
        Args:
            image: PIL Image to encode
            
        Returns:
            List of crop embeddings
        """
        crops = self.generate_crops(image, config.NUM_CROPS)
        crop_embeddings = []
        
        for crop in crops:
            emb = self.encode_image(crop)
            crop_embeddings.append(emb)
        
        return crop_embeddings
    
    def compute_local_score(self, image: Image.Image, query_embedding: np.ndarray) -> float:
        """
        Compute local score by finding max similarity across crops.
        
        Args:
            image: PIL Image to score
            query_embedding: Query embedding vector
            
        Returns:
            Maximum similarity score across all crops
        """
        crop_embeddings = self.encode_image_local(image)
        similarities = []
        
        for crop_emb in crop_embeddings:
            similarity = self.compute_similarity(query_embedding, crop_emb)
            similarities.append(similarity)
        
        return float(max(similarities))
    
    def zero_shot_classify(self, image: Image.Image, query: str, threshold: float = 0.5) -> tuple:
        """
        Zero-shot classification: Does this image contain the query concept?
        
        Args:
            image: PIL Image to classify
            query: Query concept
            threshold: Confidence threshold
            
        Returns:
            (contains_concept: bool, confidence: float)
        """
        # Positive prompts
        positive_prompts = [
            f"a photo of {query}",
            f"{query}",
            f"an image containing {query}"
        ]
        
        # Negative prompts
        negative_prompts = [
            "a photo without any specific subject",
            "an empty scene",
            "a landscape or nature scene"
        ]
        
        # Encode image
        image_embedding = self.encode_image(image)
        
        # Compute positive scores
        positive_scores = []
        for prompt in positive_prompts:
            text_emb = self.encode_text(prompt)
            score = self.compute_similarity(text_emb, image_embedding)
            positive_scores.append(score)
        
        # Compute negative scores
        negative_scores = []
        for prompt in negative_prompts:
            text_emb = self.encode_text(prompt)
            score = self.compute_similarity(text_emb, image_embedding)
            negative_scores.append(score)
        
        # Average scores
        avg_positive = np.mean(positive_scores)
        avg_negative = np.mean(negative_scores)
        
        # Confidence: normalized difference
        confidence = (avg_positive - avg_negative + 1.0) / 2.0
        
        # Decision
        contains_concept = confidence > threshold
        
        return contains_concept, float(confidence)


# Global singleton instance
_embedding_service = None


def get_embedding_service() -> CLIPEmbeddingService:
    """Get or create embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = CLIPEmbeddingService()
    return _embedding_service
