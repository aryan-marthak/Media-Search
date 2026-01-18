"""
Face clustering service using DBSCAN algorithm.
"""
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple
import uuid

from database import get_db_connection


class ClusteringService:
    """Service for clustering faces into people."""
    
    def __init__(self):
        """Initialize clustering service."""
        self.eps = 0.35  # Distance threshold (balanced for good matching)
        self.min_samples = 2  # Minimum faces to form a cluster
        print(f">> Clustering Service initialized (eps={self.eps}, min_samples={self.min_samples})")
    
    def cluster_faces(self) -> Dict[str, int]:
        """
        Cluster all unassigned faces using DBSCAN.
        
        Returns:
            Dictionary with statistics: {
                'total_faces': int,
                'clustered': int,
                'clusters_created': int,
                'outliers': int
            }
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all faces without cluster assignment
        cursor.execute("""
            SELECT id, face_embedding 
            FROM faces 
            WHERE cluster_id IS NULL
        """)
        rows = cursor.fetchall()
        
        if len(rows) == 0:
            cursor.close()
            conn.close()
            return {
                'total_faces': 0,
                'clustered': 0,
                'clusters_created': 0,
                'outliers': 0
            }
        
        # Extract face IDs and embeddings
        face_ids = [row['id'] for row in rows]
        embeddings = np.array([row['face_embedding'] for row in rows])
        
        print(f">> Clustering {len(face_ids)} faces...")
        
        # Compute cosine distance matrix
        # DBSCAN uses distance, so we convert similarity to distance
        similarity_matrix = cosine_similarity(embeddings)
        
        # Clip similarity to [-1, 1] to avoid floating point errors
        similarity_matrix = np.clip(similarity_matrix, -1.0, 1.0)
        
        # Convert to distance and ensure non-negative
        distance_matrix = 1 - similarity_matrix
        distance_matrix = np.maximum(distance_matrix, 0)  # Ensure no negative values
        
        # Run DBSCAN clustering
        clustering = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric='precomputed'
        )
        labels = clustering.fit_predict(distance_matrix)
        
        # Process clustering results
        unique_labels = set(labels)
        clusters_created = 0
        clustered_count = 0
        outlier_count = 0
        
        for label in unique_labels:
            if label == -1:
                # Outliers (noise points)
                outlier_count = np.sum(labels == -1)
                continue
            
            # Get faces in this cluster
            cluster_mask = labels == label
            cluster_face_ids = [face_ids[i] for i, mask in enumerate(cluster_mask) if mask]
            cluster_embeddings = embeddings[cluster_mask]
            
            # Create new cluster
            cluster_id = str(uuid.uuid4())
            
            # Find representative face (most central)
            centroid = np.mean(cluster_embeddings, axis=0)
            distances_to_centroid = np.linalg.norm(cluster_embeddings - centroid, axis=1)
            representative_idx = np.argmin(distances_to_centroid)
            representative_face_id = cluster_face_ids[representative_idx]
            
            # Insert cluster
            cursor.execute("""
                INSERT INTO face_clusters (id, representative_face_id, face_count)
                VALUES (%s, %s, %s)
            """, (cluster_id, representative_face_id, len(cluster_face_ids)))
            
            # Assign cluster_id to all faces in cluster
            for face_id in cluster_face_ids:
                cursor.execute("""
                    UPDATE faces 
                    SET cluster_id = %s 
                    WHERE id = %s
                """, (cluster_id, face_id))
            
            clusters_created += 1
            clustered_count += len(cluster_face_ids)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        stats = {
            'total_faces': int(len(face_ids)),
            'clustered': int(clustered_count),
            'clusters_created': int(clusters_created),
            'outliers': int(outlier_count)
        }
        
        print(f">> Clustering complete: {clusters_created} clusters, {clustered_count} faces clustered, {outlier_count} outliers")
        return stats
    
    def recluster_all(self) -> Dict[str, int]:
        """
        Re-cluster all faces (reset and cluster from scratch).
        
        Returns:
            Clustering statistics
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Reset all cluster assignments
        cursor.execute("UPDATE faces SET cluster_id = NULL")
        
        # Delete all clusters
        cursor.execute("DELETE FROM face_clusters")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Run clustering
        return self.cluster_faces()


# Singleton instance
_clustering_service = None


def get_clustering_service() -> ClusteringService:
    """Get or create ClusteringService singleton."""
    global _clustering_service
    if _clustering_service is None:
        _clustering_service = ClusteringService()
    return _clustering_service
