"""
Debug Deep Search matching to see why beach appears in forest search.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import config
import numpy as np
from embedding_service import get_embedding_service

def debug_deep_search(query: str):
    """Debug Deep Search to see matching scores."""
    
    print(f"🔍 Debugging Deep Search for: '{query}'")
    print("="*80)
    
    # Get embedding service
    embedding_service = get_embedding_service()
    
    # Encode query
    query_embedding = embedding_service.encode_text(query)
    print(f"\n✅ Query encoded\n")
    
    # Get all VLM descriptions
    conn = psycopg2.connect(config.DATABASE_URL, cursor_factory=RealDictCursor)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, file_path, vlm_description
        FROM images
        WHERE vlm_processed = TRUE AND vlm_description IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    print(f"Found {len(rows)} images with VLM descriptions\n")
    print("="*80)
    print("MATCHING SCORES:")
    print("="*80)
    
    # Calculate scores
    results = []
    for row in rows:
        desc = row['vlm_description']
        desc_embedding = embedding_service.encode_text(desc)
        similarity = float(np.dot(query_embedding, desc_embedding))
        
        results.append({
            'id': row['id'],
            'file': row['file_path'],
            'description': desc,
            'score': similarity
        })
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Show top 5
    for i, result in enumerate(results[:5], 1):
        print(f"\n{i}. Score: {result['score']:.4f}")
        print(f"   File: {result['file']}")
        print(f"   Description: {result['description'][:150]}...")
        print()
    
    print("="*80)
    print(f"Score threshold: {config.SCORE_THRESHOLD}")
    print(f"Images above threshold: {sum(1 for r in results if r['score'] >= config.SCORE_THRESHOLD)}")

if __name__ == "__main__":
    debug_deep_search("green forest and mountains")
