"""
Face clustering service using DBSCAN algorithm.
"""
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict
import uuid

from database import get_db_connection


class ClusteringService:
    """Service for clustering faces into people."""
    
    def __init__(self):
        """Initialize clustering service."""
        self.eps = 0.42  # Distance threshold (more lenient - merges same person with variations)
        self.min_samples = 1  # Allow single-face clusters (user will manually group)
        print(f">> Clustering Service initialized (eps={self.eps}, min_samples={self.min_samples})")
    
    def cluster_faces_for_user(self, user_id: str) -> Dict[str, int]:
        """
        Cluster all unassigned faces for a specific user using DBSCAN.

        Args:
            user_id: The user whose unassigned faces to cluster.

        Returns:
            Statistics dict with total_faces, clustered, clusters_created, outliers.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        # Only fetch faces from this user's images
        cursor.execute("""
            SELECT f.id, f.face_embedding
            FROM faces f
            JOIN images i ON f.image_id = i.id
            WHERE f.cluster_id IS NULL AND i.user_id = %s
        """, (user_id,))
        rows = cursor.fetchall()

        if len(rows) == 0:
            cursor.close()
            conn.close()
            return {'total_faces': 0, 'clustered': 0, 'clusters_created': 0, 'outliers': 0}

        face_ids = [row['id'] for row in rows]
        embeddings = np.array([row['face_embedding'] for row in rows])

        print(f">> Clustering {len(face_ids)} faces for user {user_id[:8]}...")

        similarity_matrix = cosine_similarity(embeddings)
        similarity_matrix = np.clip(similarity_matrix, -1.0, 1.0)
        distance_matrix = np.maximum(1 - similarity_matrix, 0)

        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric='precomputed')
        labels = clustering.fit_predict(distance_matrix)

        unique_labels = set(labels)
        clusters_created = 0
        clustered_count = 0
        outlier_count = int(np.sum(labels == -1))

        for label in unique_labels:
            if label == -1:
                continue

            cluster_mask = labels == label
            cluster_face_ids = [face_ids[i] for i, m in enumerate(cluster_mask) if m]
            cluster_embeddings = embeddings[cluster_mask]

            cluster_id = str(uuid.uuid4())
            representative_embedding = np.mean(cluster_embeddings, axis=0)
            similarities = cosine_similarity([representative_embedding], cluster_embeddings)[0]
            representative_face_id = cluster_face_ids[int(np.argmax(similarities))]

            cursor.execute("""
                INSERT INTO face_clusters (id, user_id, name, representative_face_id, face_count)
                VALUES (%s, %s, %s, %s, %s)
            """, (cluster_id, user_id, f"Person {clusters_created + 1}", representative_face_id, len(cluster_face_ids)))

            for face_id in cluster_face_ids:
                cursor.execute("UPDATE faces SET cluster_id = %s WHERE id = %s", (cluster_id, face_id))

            clusters_created += 1
            clustered_count += len(cluster_face_ids)

        conn.commit()
        cursor.close()
        conn.close()

        stats = {
            'total_faces': len(face_ids),
            'clustered': clustered_count,
            'clusters_created': clusters_created,
            'outliers': outlier_count,
        }
        print(f">> Clustering complete: {clusters_created} clusters, {clustered_count} faces, {outlier_count} outliers")
        return stats


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
        
        face_ids = [row['id'] for row in rows]
        embeddings = np.array([row['face_embedding'] for row in rows])
        
        print(f">> Clustering {len(face_ids)} faces...")
        
        similarity_matrix = cosine_similarity(embeddings)
        similarity_matrix = np.clip(similarity_matrix, -1.0, 1.0)
        distance_matrix = 1 - similarity_matrix
        distance_matrix = np.maximum(distance_matrix, 0)
        
        clustering = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric='precomputed'
        )
        labels = clustering.fit_predict(distance_matrix)
        
        unique_labels = set(labels)
        clusters_created = 0
        clustered_count = 0
        outlier_count = 0
        
        for label in unique_labels:
            if label == -1:
                outlier_count = np.sum(labels == -1)
                continue
            
            cluster_mask = labels == label
            cluster_face_ids = [face_ids[i] for i, mask in enumerate(cluster_mask) if mask]
            cluster_embeddings = embeddings[cluster_mask]
            
            cluster_id = str(uuid.uuid4())
            
            representative_embedding = np.mean(cluster_embeddings, axis=0)
            similarities = cosine_similarity([representative_embedding], cluster_embeddings)[0]
            representative_idx = np.argmax(similarities)
            representative_face_id = cluster_face_ids[representative_idx]
            
            cursor.execute("""
                INSERT INTO face_clusters (id, name, representative_face_id, face_count)
                VALUES (%s, %s, %s, %s)
            """, (cluster_id, f"Person {clusters_created + 1}", representative_face_id, len(cluster_face_ids)))
            
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
            'total_faces': len(face_ids),
            'clustered': clustered_count,
            'clusters_created': clusters_created,
            'outliers': outlier_count
        }
        
        print(f">> Clustering complete: {clusters_created} clusters, {clustered_count} faces clustered, {outlier_count} outliers")
        return stats
    
    def merge_clusters(self, cluster_ids: List[str], new_name: str) -> Dict[str, any]:
        """
        Merge multiple clusters into one.
        
        Args:
            cluster_ids: List of cluster IDs to merge
            new_name: Name for the merged cluster
            
        Returns:
            Dictionary with merge statistics
        """
        if len(cluster_ids) < 2:
            raise ValueError("Need at least 2 clusters to merge")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        primary_cluster_id = cluster_ids[0]
        secondary_cluster_ids = cluster_ids[1:]
        
        for cluster_id in secondary_cluster_ids:
            cursor.execute("""
                UPDATE faces 
                SET cluster_id = %s 
                WHERE cluster_id = %s
            """, (primary_cluster_id, cluster_id))
        
        cursor.execute("""
            DELETE FROM face_clusters 
            WHERE id = ANY(%s)
        """, (secondary_cluster_ids,))
        
        cursor.execute("""
            UPDATE face_clusters 
            SET name = %s,
                face_count = (SELECT COUNT(*) FROM faces WHERE cluster_id = %s)
            WHERE id = %s
        """, (new_name, primary_cluster_id, primary_cluster_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'merged_cluster_id': primary_cluster_id,
            'clusters_merged': len(secondary_cluster_ids) + 1
        }


# Singleton instance
_clustering_service = None


def get_clustering_service() -> ClusteringService:
    """Get or create ClusteringService singleton."""
    global _clustering_service
    if _clustering_service is None:
        _clustering_service = ClusteringService()
    return _clustering_service
