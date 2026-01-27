"""
Check how many images have VLM descriptions vs total images.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import config

def check_vlm_coverage():
    """Check VLM description coverage."""
    
    print("📊 VLM Description Coverage")
    print("="*80)
    
    conn = psycopg2.connect(config.DATABASE_URL, cursor_factory=RealDictCursor)
    cursor = conn.cursor()
    
    # Total images
    cursor.execute("SELECT COUNT(*) as total FROM images")
    total = cursor.fetchone()['total']
    
    # Images with VLM
    cursor.execute("""
        SELECT COUNT(*) as with_vlm 
        FROM images 
        WHERE vlm_processed = TRUE AND vlm_description IS NOT NULL
    """)
    with_vlm = cursor.fetchone()['with_vlm']
    
    # Images without VLM
    without_vlm = total - with_vlm
    
    cursor.close()
    conn.close()
    
    print(f"\nTotal images: {total}")
    print(f"With VLM descriptions: {with_vlm} ({with_vlm/total*100:.1f}%)")
    print(f"Without VLM descriptions: {without_vlm} ({without_vlm/total*100:.1f}%)")
    
    print("\n" + "="*80)
    
    if without_vlm > 0:
        print(f"\n⚠️  {without_vlm} images need VLM processing!")
        print("\nTo fix:")
        print("1. Use the /reprocess-vlm endpoint to generate descriptions")
        print("2. Or upload images again with VLM enabled")
        print(f"\nEstimated time: {without_vlm * 5.5 / 60:.1f} minutes (~5.5s per image)")
    else:
        print("\n✅ All images have VLM descriptions!")

if __name__ == "__main__":
    check_vlm_coverage()
