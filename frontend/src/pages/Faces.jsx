import { useState, useEffect } from 'react'
import { Users, Edit2, Check, X } from 'lucide-react'
import { facesApi } from '../api/faces'
import { imagesApi } from '../api/images'

function Faces() {
    const [clusters, setClusters] = useState([])
    const [loading, setLoading] = useState(true)
    const [selectedCluster, setSelectedCluster] = useState(null)
    const [clusterImages, setClusterImages] = useState([])
    const [editingId, setEditingId] = useState(null)
    const [editName, setEditName] = useState('')

    useEffect(() => {
        fetchClusters()
    }, [])

    const fetchClusters = async () => {
        try {
            const data = await facesApi.getClusters()
            setClusters(data)
        } catch (err) {
            console.error('Failed to fetch face clusters:', err)
        } finally {
            setLoading(false)
        }
    }

    const handleClusterClick = async (cluster) => {
        setSelectedCluster(cluster)
        try {
            const images = await facesApi.getClusterImages(cluster.id)
            setClusterImages(images)
        } catch (err) {
            console.error('Failed to fetch cluster images:', err)
        }
    }

    const handleRename = async (clusterId) => {
        if (!editName.trim()) {
            setEditingId(null)
            return
        }

        try {
            await facesApi.updateClusterName(clusterId, editName)
            setClusters(prev => prev.map(c =>
                c.id === clusterId ? { ...c, name: editName } : c
            ))
            if (selectedCluster?.id === clusterId) {
                setSelectedCluster({ ...selectedCluster, name: editName })
            }
        } catch (err) {
            console.error('Failed to rename cluster:', err)
        }

        setEditingId(null)
        setEditName('')
    }

    if (loading) {
        return (
            <div className="loading-screen" style={{ minHeight: '50vh' }}>
                <div className="loading-spinner"></div>
            </div>
        )
    }

    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">Faces</h1>
            </div>

            {clusters.length === 0 ? (
                <div className="empty-state">
                    <Users className="empty-state-icon" />
                    <h3>No faces detected yet</h3>
                    <p>Upload photos with faces to start building your face library</p>
                </div>
            ) : (
                <div style={{ display: 'flex', gap: 'var(--spacing-xl)' }}>
                    {/* Clusters list */}
                    <div style={{ flex: '0 0 300px' }}>
                        <h3 style={{ marginBottom: 'var(--spacing-md)', color: 'var(--text-secondary)' }}>
                            People ({clusters.length})
                        </h3>
                        <div className="face-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
                            {clusters.map((cluster) => (
                                <div
                                    key={cluster.id}
                                    className={`face-cluster-card ${selectedCluster?.id === cluster.id ? 'active' : ''}`}
                                    onClick={() => handleClusterClick(cluster)}
                                    style={selectedCluster?.id === cluster.id ? {
                                        borderColor: 'var(--accent-primary)',
                                        boxShadow: 'var(--shadow-glow)'
                                    } : {}}
                                >
                                    {cluster.representative_face_path ? (
                                        <img
                                            src={imagesApi.getImageUrl(cluster.representative_face_path)}
                                            alt={cluster.name || 'Unknown'}
                                            className="face-thumbnail"
                                        />
                                    ) : (
                                        <div className="face-thumbnail" style={{
                                            background: 'var(--accent-gradient)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            fontSize: '1.5rem',
                                            color: 'white'
                                        }}>
                                            {cluster.name ? cluster.name.charAt(0).toUpperCase() : '?'}
                                        </div>
                                    )}

                                    {editingId === cluster.id ? (
                                        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                                            <input
                                                type="text"
                                                className="input"
                                                value={editName}
                                                onChange={(e) => setEditName(e.target.value)}
                                                placeholder="Name"
                                                style={{ padding: '4px 8px', fontSize: '0.875rem' }}
                                                autoFocus
                                                onClick={(e) => e.stopPropagation()}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') handleRename(cluster.id)
                                                    if (e.key === 'Escape') { setEditingId(null); setEditName('') }
                                                }}
                                            />
                                            <button
                                                className="btn btn-ghost btn-icon"
                                                onClick={(e) => { e.stopPropagation(); handleRename(cluster.id) }}
                                                style={{ padding: '4px' }}
                                            >
                                                <Check size={14} />
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="face-name" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                            {cluster.name || 'Unknown'}
                                            <button
                                                className="btn btn-ghost btn-icon"
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    setEditingId(cluster.id)
                                                    setEditName(cluster.name || '')
                                                }}
                                                style={{ padding: '2px' }}
                                            >
                                                <Edit2 size={12} />
                                            </button>
                                        </div>
                                    )}

                                    <div className="face-count">{cluster.image_count} photos</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Selected cluster images */}
                    <div style={{ flex: 1 }}>
                        {selectedCluster ? (
                            <>
                                <h3 style={{ marginBottom: 'var(--spacing-md)' }}>
                                    Photos of {selectedCluster.name || 'Unknown Person'}
                                </h3>
                                <div className="image-grid">
                                    {clusterImages.map((image) => (
                                        <div key={image.id} className="image-card">
                                            <img
                                                src={imagesApi.getImageUrl(image.thumbnail_path)}
                                                alt={image.filename}
                                                loading="lazy"
                                            />
                                        </div>
                                    ))}
                                </div>
                            </>
                        ) : (
                            <div className="empty-state">
                                <p>Select a person to see their photos</p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}

export default Faces
