"""
Batch process existing images to generate VLM descriptions.
Run this script to add Deep Search support to images uploaded before VLM was enabled.
"""
import psycopg2
from PIL import Image
from pathlib import Path
import config
from vlm_service import get_vlm_service

def process_images():
    """Generate VLM descriptions for all images without them."""
    
    # Get VLM service
    vlm_service = get_vlm_service()
    if not vlm_service.is_available():
        print(">> ❌ VLM service not available. Make sure ENABLE_VLM=true")
        return
    
    # Connect to database
    conn = psycopg2.connect(config.DATABASE_URL)
    cursor = conn.cursor()
    
    # Get all images without VLM descriptions
    cursor.execute("""
        SELECT id, file_path 
        FROM images 
        WHERE vlm_processed = FALSE OR vlm_description IS NULL
        ORDER BY created_at DESC
    """)
    
    images = cursor.fetchall()
    total = len(images)
    
    if total == 0:
        print(">> ✅ All images already have VLM descriptions!")
        return
    
    print(f">> Found {total} images to process")
    print(">> This may take a while...")
    
    processed = 0
    failed = 0
    
    for image_id, file_path in images:
        try:
            # Load image
            image = Image.open(file_path).convert("RGB")
            
            # Generate VLM description
            print(f">> Processing {image_id}... ({processed + 1}/{total})")
            description = vlm_service.generate_caption(image)
            
            if description:
                # Update database
                cursor.execute(
                    "UPDATE images SET vlm_description = %s, vlm_processed = TRUE WHERE id = %s",
                    (description, image_id)
                )
                conn.commit()
                print(f"   ✅ {description[:80]}...")
                processed += 1
            else:
                print(f"   ⚠️  No description generated")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            failed += 1
            continue
    
    cursor.close()
    conn.close()
    
    print(f"\n>> ✅ Processing complete!")
    print(f"   - Processed: {processed}")
    print(f"   - Failed: {failed}")
    print(f"   - Total: {total}")
    print(f"\n>> Deep Search is now available for {processed} images!")

if __name__ == "__main__":
    process_images()
