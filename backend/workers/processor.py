import asyncio
from datetime import datetime
from uuid import UUID
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import numpy as np

from config import DATABASE_URL, IMAGES_DIR, DEVICE
from models import Image as ImageModel, Face, FaceCluster
from services.embeddings import encode_image
# VLM disabled for performance - using SigLIP embeddings only
# from services.vlm import extract_metadata
# from services.vocabulary import normalize_metadata
from services.qdrant import upsert_image_embedding, upsert_face_embedding
from services.events import event_bus, StatusEvent


# Create separate engine for background tasks
_bg_engine = None
_bg_session_maker = None

# Face detection and embedding models (lazy loaded)
_mtcnn = None
_resnet = None


def get_bg_session_maker():
    """Get session maker for background tasks."""
    global _bg_engine, _bg_session_maker
    
    if _bg_engine is None:
        _bg_engine = create_async_engine(DATABASE_URL, echo=False)
        _bg_session_maker = async_sessionmaker(_bg_engine, expire_on_commit=False)
    
    return _bg_session_maker


def get_face_models():
    """Get or initialize the face detection and embedding models."""
    global _mtcnn, _resnet
    
    if _mtcnn is None:
        try:
            import torch
            from facenet_pytorch import MTCNN, InceptionResnetV1
            
            device = torch.device(DEVICE if torch.cuda.is_available() else 'cpu')
            
            # MTCNN for face detection
            _mtcnn = MTCNN(
                keep_all=True,  # Return all faces
                device=device,
                select_largest=False
            )
            
            # InceptionResnetV1 for face embeddings (512-dim)
            # Using VGGFace2 pretrained weights
            _resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)
            
            print(f"✅ Face models loaded on {device}")
        except Exception as e:
            print(f"⚠️ Failed to load face models: {e}")
            return None, None
    
    return _mtcnn, _resnet


async def process_image_task(image_id: str):
    """
    Background task to process an uploaded image.
    
    Pipeline:
    1. Load image from filesystem
    2. Generate SigLIP embedding
    3. Extract metadata with VLM
    4. Normalize metadata vocabulary
    5. Upsert to Qdrant
    6. Update database status
    7. Process faces (optional)
    """
    import time
    
    session_maker = get_bg_session_maker()
    
    async with session_maker() as db:
        try:
            total_start = time.time()
            
            # Get image record
            result = await db.execute(
                select(ImageModel).where(ImageModel.id == UUID(image_id))
            )
            image = result.scalar_one_or_none()
            
            if not image:
                print(f"❌ Image not found: {image_id}")
                return
            
            # Update status to processing
            image.processing_status = "processing"
            await db.commit()
            
            print(f"🔄 Processing image: {image_id}")
            
            # Load image file
            file_path = IMAGES_DIR.parent / image.file_path
            pil_image = Image.open(file_path).convert("RGB")
            
            # Step 1: Generate SigLIP embedding
            step_start = time.time()
            print(f"  📊 Generating embedding...")
            embedding = encode_image(pil_image)
            embedding_time = time.time() - step_start
            print(f"     ⏱️ Embedding: {embedding_time:.2f}s")
            
            # Step 2: Skip VLM - use empty metadata for fast processing
            # VLM disabled due to performance issues (11+ min per image on RTX 3050)
            # SigLIP embeddings alone provide good semantic search capability
            metadata = {
                "objects": [],
                "action": None,
                "time": None,
                "scene": None,
                "weather": None,
                "emotion": None,
                "caption": None
            }
            
            # Add file info to metadata for Qdrant payload
            metadata["filename"] = image.filename
            metadata["thumbnail_path"] = image.thumbnail_path
            metadata["original_filename"] = image.original_filename
            
            # Step 4: Upsert to Qdrant
            step_start = time.time()
            print(f"  💾 Storing in Qdrant...")
            await upsert_image_embedding(
                user_id=str(image.owner_id),
                image_id=image_id,
                embedding=embedding,
                metadata=metadata
            )
            qdrant_time = time.time() - step_start
            print(f"     ⏱️ Qdrant: {qdrant_time:.2f}s")
            
            # Step 5: Update database
            image.processing_status = "completed"
            image.processed_at = datetime.utcnow()
            await db.commit()
            
            # Publish SSE event
            await event_bus.publish(
                str(image.owner_id),
                StatusEvent(image_id=image_id, status="completed")
            )
            
            total_time = time.time() - total_start
            print(f"✅ Completed: {image_id} (Total: {total_time:.2f}s)")
            
            # Step 6: Process faces in background (non-blocking)
            step_start = time.time()
            try:
                await process_faces_for_image(image_id, pil_image, str(image.owner_id))
                face_time = time.time() - step_start
                print(f"     ⏱️ Faces: {face_time:.2f}s")
            except Exception as e:
                print(f"  ⚠️ Face processing failed (non-critical): {e}")
            
        except Exception as e:
            print(f"❌ Error processing {image_id}: {e}")
            
            # Update status to failed
            try:
                result = await db.execute(
                    select(ImageModel).where(ImageModel.id == UUID(image_id))
                )
                image = result.scalar_one_or_none()
                if image:
                    image.processing_status = "failed"
                    image.processing_error = str(e)[:500]
                    await db.commit()
                    
                    # Publish SSE event
                    await event_bus.publish(
                        str(image.owner_id),
                        StatusEvent(image_id=image_id, status="failed", error=str(e)[:200])
                    )
            except Exception:
                pass


async def process_faces_for_image(image_id: str, pil_image: Image.Image, owner_id: str):
    """
    Background task to detect and process faces using facenet-pytorch.
    
    Pipeline:
    1. Detect faces with MTCNN
    2. Generate face embeddings (InceptionResnetV1 - 512-dim)
    3. Store in Qdrant
    4. Create face records in database
    """
    import torch
    
    mtcnn, resnet = get_face_models()
    if mtcnn is None or resnet is None:
        return
    
    session_maker = get_bg_session_maker()
    
    try:
        # Detect faces and get bounding boxes
        boxes, probs = mtcnn.detect(pil_image)
        
        if boxes is None or len(boxes) == 0:
            return
        
        # Get face crops for embedding
        faces = mtcnn(pil_image)
        
        if faces is None:
            return
        
        print(f"  👤 Found {len(faces)} face(s)")
        
        # Move faces to same device as model and generate embeddings
        device = torch.device(DEVICE if torch.cuda.is_available() else 'cpu')
        faces = faces.to(device)
        
        # Generate embeddings
        with torch.no_grad():
            embeddings = resnet(faces).cpu().numpy()
        
        async with session_maker() as db:
            for i, (box, embedding) in enumerate(zip(boxes, embeddings)):
                # Normalize embedding
                embedding = embedding / np.linalg.norm(embedding)
                
                # Get bounding box
                x1, y1, x2, y2 = box.astype(int)
                
                # Create face record
                face_record = Face(
                    image_id=UUID(image_id),
                    bbox_x=str(max(0, x1)),
                    bbox_y=str(max(0, y1)),
                    bbox_width=str(max(0, x2 - x1)),
                    bbox_height=str(max(0, y2 - y1))
                )
                db.add(face_record)
                await db.flush()
                
                # Store face embedding in Qdrant
                await upsert_face_embedding(
                    user_id=owner_id,
                    face_id=str(face_record.id),
                    embedding=embedding,
                    metadata={
                        "image_id": image_id,
                        "face_id": str(face_record.id)
                    }
                )
            
            await db.commit()
            print(f"  ✅ Processed {len(faces)} faces for image {image_id}")
            
    except Exception as e:
        print(f"  ⚠️ Face detection error: {e}")
