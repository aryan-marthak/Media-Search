import { useState, useEffect } from 'react'
import { Share2, X } from 'lucide-react'
import { sharesApi } from '../api/shares'
import { imagesApi } from '../api/images'

function SharedWithMe() {
    const [sharedImages, setSharedImages] = useState([])
    const [loading, setLoading] = useState(true)
    const [selectedImage, setSelectedImage] = useState(null)

    useEffect(() => {
        fetchSharedImages()
    }, [])

    const fetchSharedImages = async () => {
        try {
            const data = await sharesApi.getSharesWithMe()
            setSharedImages(data)
        } catch (err) {
            console.error('Failed to fetch shared images:', err)
        } finally {
            setLoading(false)
        }
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
                <h1 className="page-title">Shared With Me</h1>
            </div>

            {sharedImages.length === 0 ? (
                <div className="empty-state">
                    <Share2 className="empty-state-icon" />
                    <h3>No shared images</h3>
                    <p>Images shared with you will appear here</p>
                </div>
            ) : (
                <div className="image-grid">
                    {sharedImages.map((share) => (
                        <div
                            key={share.id}
                            className="image-card"
                            onClick={() => setSelectedImage(share)}
                        >
                            <img
                                src={imagesApi.getImageUrl(share.thumbnail_path)}
                                alt={share.filename}
                                loading="lazy"
                            />
                            <div className="image-card-overlay">
                                <div>
                                    <div style={{ color: 'white', fontSize: '0.875rem' }}>
                                        {share.filename}
                                    </div>
                                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                                        Shared by {share.owner_username}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Lightbox */}
            {selectedImage && (
                <div className="lightbox" onClick={() => setSelectedImage(null)}>
                    <button className="lightbox-close">
                        <X size={24} />
                    </button>
                    <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
                        <img
                            src={imagesApi.getImageUrl(selectedImage.thumbnail_path)}
                            alt={selectedImage.filename}
                        />
                    </div>
                    <div style={{
                        position: 'absolute',
                        bottom: 'var(--spacing-xl)',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        background: 'var(--bg-card)',
                        padding: 'var(--spacing-md)',
                        borderRadius: 'var(--radius-lg)',
                        backdropFilter: 'blur(10px)',
                        textAlign: 'center'
                    }}>
                        <div style={{ color: 'var(--text-primary)' }}>
                            {selectedImage.filename}
                        </div>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                            Shared by {selectedImage.owner_username}
                        </div>
                        <div style={{
                            marginTop: 'var(--spacing-xs)',
                            fontSize: '0.75rem',
                            color: 'var(--text-muted)'
                        }}>
                            Permission: {selectedImage.permission}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default SharedWithMe
