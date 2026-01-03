import { useState, useEffect, useCallback, useRef } from 'react'
import { Upload, Plus, X, Image as ImageIcon, Trash2, CheckSquare, Square } from 'lucide-react'
import { imagesApi } from '../api/images'
import { useAuth } from '../context/AuthContext'

function Gallery() {
    const [images, setImages] = useState([])
    const [loading, setLoading] = useState(true)
    const [uploading, setUploading] = useState(false)
    const [showUpload, setShowUpload] = useState(false)
    const [dragging, setDragging] = useState(false)
    const [selectedImage, setSelectedImage] = useState(null)
    const [selectMode, setSelectMode] = useState(false)
    const [selectedIds, setSelectedIds] = useState(new Set())
    const [deleting, setDeleting] = useState(false)
    const { token } = useAuth()
    const eventSourceRef = useRef(null)

    const fetchImages = useCallback(async () => {
        try {
            const data = await imagesApi.list()
            setImages(data.images)
        } catch (err) {
            console.error('Failed to fetch images:', err)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchImages()
    }, [fetchImages])

    // Poll for status updates when images are pending/processing
    useEffect(() => {
        const pendingImages = images.filter(
            img => img.processing_status === 'pending' || img.processing_status === 'processing'
        )

        if (pendingImages.length === 0) return

        console.log(`Polling: ${pendingImages.length} images in progress`)

        const interval = setInterval(async () => {
            try {
                const data = await imagesApi.list()
                setImages(data.images)

                // Check if all done, stop polling
                const stillProcessing = data.images.filter(
                    img => img.processing_status === 'pending' || img.processing_status === 'processing'
                )
                if (stillProcessing.length === 0) {
                    console.log('Polling: All images processed')
                    clearInterval(interval)
                }
            } catch (err) {
                console.error('Polling error:', err)
            }
        }, 3000)  // Poll every 3 seconds

        return () => clearInterval(interval)
    }, [images.filter(img => img.processing_status === 'pending' || img.processing_status === 'processing').length])

    const handleDragOver = (e) => {
        e.preventDefault()
        setDragging(true)
    }

    const handleDragLeave = (e) => {
        e.preventDefault()
        setDragging(false)
    }

    const handleDrop = async (e) => {
        e.preventDefault()
        setDragging(false)

        const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'))
        if (files.length > 0) {
            await uploadFiles(files)
        }
    }

    const handleFileSelect = async (e) => {
        const files = Array.from(e.target.files)
        if (files.length > 0) {
            await uploadFiles(files)
        }
    }

    const uploadFiles = async (files) => {
        setUploading(true)
        try {
            const uploaded = await imagesApi.upload(files)
            setImages(prev => [...uploaded, ...prev])
            setShowUpload(false)
        } catch (err) {
            console.error('Upload failed:', err)
        } finally {
            setUploading(false)
        }
    }

    const handleDelete = async (imageId) => {
        if (!confirm('Delete this image?')) return

        try {
            await imagesApi.delete(imageId)
            setImages(prev => prev.filter(img => img.id !== imageId))
            setSelectedImage(null)
        } catch (err) {
            console.error('Delete failed:', err)
        }
    }

    const handleBulkDelete = async () => {
        if (selectedIds.size === 0) return
        if (!confirm(`Delete ${selectedIds.size} selected image(s)?`)) return

        setDeleting(true)
        try {
            // Delete all selected images
            await Promise.all(
                Array.from(selectedIds).map(id => imagesApi.delete(id))
            )
            setImages(prev => prev.filter(img => !selectedIds.has(img.id)))
            setSelectedIds(new Set())
            setSelectMode(false)
        } catch (err) {
            console.error('Bulk delete failed:', err)
        } finally {
            setDeleting(false)
        }
    }

    const toggleSelect = (imageId) => {
        setSelectedIds(prev => {
            const newSet = new Set(prev)
            if (newSet.has(imageId)) {
                newSet.delete(imageId)
            } else {
                newSet.add(imageId)
            }
            return newSet
        })
    }

    const selectAll = () => {
        if (selectedIds.size === images.length) {
            setSelectedIds(new Set())
        } else {
            setSelectedIds(new Set(images.map(img => img.id)))
        }
    }

    const exitSelectMode = () => {
        setSelectMode(false)
        setSelectedIds(new Set())
    }

    const handleImageClick = (image) => {
        if (selectMode) {
            toggleSelect(image.id)
        } else {
            setSelectedImage(image)
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
                <h1 className="page-title">Gallery</h1>
                <div className="page-actions">
                    {selectMode ? (
                        <>
                            <span style={{ color: 'var(--text-secondary)', marginRight: 'var(--spacing-sm)' }}>
                                {selectedIds.size} selected
                            </span>
                            <button className="btn btn-secondary" onClick={selectAll}>
                                {selectedIds.size === images.length ? 'Deselect All' : 'Select All'}
                            </button>
                            <button
                                className="btn btn-primary"
                                onClick={handleBulkDelete}
                                disabled={selectedIds.size === 0 || deleting}
                                style={{ background: 'var(--error)' }}
                            >
                                <Trash2 size={18} />
                                {deleting ? 'Deleting...' : `Delete (${selectedIds.size})`}
                            </button>
                            <button className="btn btn-ghost" onClick={exitSelectMode}>
                                Cancel
                            </button>
                        </>
                    ) : (
                        <>
                            {images.length > 0 && (
                                <button className="btn btn-secondary" onClick={() => setSelectMode(true)}>
                                    <CheckSquare size={18} />
                                    Select
                                </button>
                            )}
                            <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
                                <Plus size={18} />
                                Upload
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Upload Modal */}
            {showUpload && (
                <div className="modal-overlay" onClick={() => setShowUpload(false)}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Upload Images</h3>
                            <button className="btn btn-ghost btn-icon" onClick={() => setShowUpload(false)}>
                                <X size={20} />
                            </button>
                        </div>
                        <div className="modal-body">
                            <div
                                className={`upload-zone ${dragging ? 'dragging' : ''}`}
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onDrop={handleDrop}
                                onClick={() => document.getElementById('file-input').click()}
                            >
                                <Upload className="upload-zone-icon" />
                                <h3>Drop images here</h3>
                                <p>or click to browse</p>
                                <input
                                    id="file-input"
                                    type="file"
                                    multiple
                                    accept="image/*"
                                    onChange={handleFileSelect}
                                    style={{ display: 'none' }}
                                />
                            </div>
                            {uploading && (
                                <div style={{ textAlign: 'center', marginTop: 'var(--spacing-md)' }}>
                                    <div className="loading-spinner" style={{ margin: '0 auto' }}></div>
                                    <p style={{ color: 'var(--text-secondary)', marginTop: 'var(--spacing-sm)' }}>
                                        Uploading...
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Image Grid */}
            {images.length === 0 ? (
                <div className="empty-state">
                    <ImageIcon className="empty-state-icon" />
                    <h3>No images yet</h3>
                    <p>Upload some images to get started</p>
                    <button
                        className="btn btn-primary"
                        style={{ marginTop: 'var(--spacing-md)' }}
                        onClick={() => setShowUpload(true)}
                    >
                        <Upload size={18} />
                        Upload Images
                    </button>
                </div>
            ) : (
                <div className="image-grid">
                    {images.map((image) => (
                        <div
                            key={image.id}
                            className="image-card"
                            onClick={() => handleImageClick(image)}
                            style={selectedIds.has(image.id) ? {
                                outline: '3px solid var(--accent-primary)',
                                outlineOffset: '-3px'
                            } : {}}
                        >
                            {selectMode && (
                                <div
                                    style={{
                                        position: 'absolute',
                                        top: 'var(--spacing-sm)',
                                        left: 'var(--spacing-sm)',
                                        zIndex: 10,
                                        background: selectedIds.has(image.id) ? 'var(--accent-primary)' : 'rgba(0,0,0,0.5)',
                                        borderRadius: 'var(--radius-sm)',
                                        padding: '4px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center'
                                    }}
                                >
                                    {selectedIds.has(image.id) ? (
                                        <CheckSquare size={18} color="white" />
                                    ) : (
                                        <Square size={18} color="white" />
                                    )}
                                </div>
                            )}
                            <img
                                src={imagesApi.getImageUrl(image.thumbnail_path)}
                                alt={image.original_filename}
                                loading="lazy"
                            />
                            {image.processing_status !== 'completed' && (
                                <span className={`image-status ${image.processing_status}`}>
                                    {image.processing_status}
                                </span>
                            )}
                            <div className="image-card-overlay">
                                <span style={{ color: 'white', fontSize: '0.875rem' }}>
                                    {image.original_filename}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Lightbox */}
            {selectedImage && !selectMode && (
                <div className="lightbox" onClick={() => setSelectedImage(null)}>
                    <button className="lightbox-close">
                        <X size={24} />
                    </button>
                    <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
                        <img
                            src={imagesApi.getFullImageUrl(selectedImage.file_path)}
                            alt={selectedImage.original_filename}
                        />
                    </div>
                    <div style={{
                        position: 'absolute',
                        bottom: 'var(--spacing-xl)',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        display: 'flex',
                        gap: 'var(--spacing-sm)'
                    }}>
                        <button
                            className="btn btn-secondary"
                            style={{ background: 'rgba(239, 68, 68, 0.2)', borderColor: 'var(--error)', color: 'var(--error)' }}
                            onClick={(e) => { e.stopPropagation(); handleDelete(selectedImage.id); }}
                        >
                            <Trash2 size={16} />
                            Delete
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}

export default Gallery
