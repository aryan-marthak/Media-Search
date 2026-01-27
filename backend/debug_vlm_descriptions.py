wai"""
Debug script to check VLM descriptions in database.
Shows what descriptions are stored and how they match queries.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import config

def check_vlm_descriptions():
    """Check all VLM descriptions in database."""
    
    print("🔍 Checking VLM Descriptions in Database")
    print("="*80)
    
    conn = psycopg2.connect(config.DATABASE_URL, cursor_factory=RealDictCursor)
    cursor = conn.cursor()
    
    # Get all images with VLM descriptions
    cursor.execute("""
        SELECT id, file_path, vlm_description, vlm_processed, created_at
        FROM images
        ORDER BY created_at DESC
        LIMIT 20
    """)
    
    rows = cursor.fetchall()
    
    print(f"\nTotal images: {len(rows)}")
    print(f"\nShowing last 20 images:\n")
    
    vlm_count = 0
    for i, row in enumerate(rows, 1):
        print(f"{i}. Image ID: {row['id']}")
        print(f"   File: {row['file_path']}")
        print(f"   VLM Processed: {row['vlm_processed']}")
        
        if row['vlm_description']:
            vlm_count += 1
            print(f"   Description: {row['vlm_description'][:200]}...")
        else:
            print(f"   Description: ❌ NONE")
        print()
    
    cursor.close()
    conn.close()
    
    print("="*80)
    print(f"Summary: {vlm_count}/{len(rows)} images have VLM descriptions")
    
    if vlm_count == 0:
        print("\n⚠️  NO VLM DESCRIPTIONS FOUND!")
        print("This means:")
        print("1. VLM service didn't load on backend startup")
        print("2. Or images were uploaded before VLM was enabled")
        print("\nSolution: Upload a new image to test VLM")

if __name__ == "__main__":
    check_vlm_descriptions()
