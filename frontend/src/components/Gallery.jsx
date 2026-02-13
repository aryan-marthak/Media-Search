import { useState, useEffect } from 'react';
import axios from 'axios';
import ImageCard from './ImageCard';
import Toast from './Toast';
import './Gallery.css';

function Gallery() {
    const [images, setImages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectMode, setSelectMode] = useState(false);
    const [selectedImages, setSelectedImages] = useState(new Set());
    const [selectedImage, setSelectedImage] = useState(null);
    const [toast, setToast] = useState(null);

    useEffect(() => {
        fetchGallery();
    }, []);

    const fetchGallery = async () => {
        try {
            setLoading(true);
            const response = await axios.get('http://localhost:8000/gallery');
            setImages(response.data.images);
        } catch (error) {
            console.error('Failed to fetch gallery:', error);
            showToast('Failed to load gallery', 'error');
        } finally {
            setLoading(false);
        }
    };

    const showToast = (message, type = 'info', duration = 3000) => {
        setToast({ message, type, duration });
    };

    const closeToast = () => {
        setToast(null);
    };

    const handleUpload = async (event) => {
        const files = Array.from(event.target.files);
        if (files.length === 0) return;

        const totalFiles = files.length;
        let completedFiles = 0;

        showToast(`Uploading ${totalFiles} image${totalFiles > 1 ? 's' : ''}...`, 'loading', 0);

        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);

            try {
                showToast(`Processing ${completedFiles + 1}/${totalFiles}...`, 'loading', 0);
                await axios.post('http://localhost:8000/upload', formData);
                completedFiles++;
            } catch (error) {
                console.error('Upload failed:', error);
                showToast(`Failed: ${file.name} (${completedFiles}/${totalFiles})`, 'error', 3000);
            }
        }

        showToast(
            `✨ Completed! ${completedFiles}/${totalFiles} images processed successfully`,
            'success',
            4000
        );

        fetchGallery();
        event.target.value = '';
    };

    const toggleSelectMode = () => {
        setSelectMode(!selectMode);
        setSelectedImages(new Set());
    };

    const selectAll = () => {
        const allIds = new Set(images.map(img => img.id));
        setSelectedImages(allIds);
    };

    const deselectAll = () => {
        setSelectedImages(new Set());
    };

    const toggleImageSelection = (imageId) => {
        const newSelected = new Set(selectedImages);
        if (newSelected.has(imageId)) {
            newSelected.delete(imageId);
        } else {
            newSelected.add(imageId);
        }
        setSelectedImages(newSelected);
    };

    const handleDelete = async () => {
        if (selectedImages.size === 0) return;

        const count = selectedImages.size;
        if (!confirm(`Delete ${count} image${count > 1 ? 's' : ''}?`)) return;

        showToast(`Deleting ${count} image${count > 1 ? 's' : ''}...`, 'loading', 0);

        try {
            await axios.delete('http://localhost:8000/images', {
                data: Array.from(selectedImages)
            });

            showToast(`Deleted ${count} image${count > 1 ? 's' : ''}`, 'success');

            setSelectedImages(new Set());
            setSelectMode(false);
            fetchGallery();
        } catch (error) {
            console.error('Delete failed:', error);
            showToast('Failed to delete images', 'error');
        }
    };

    // Group images by date
    const groupImagesByDate = (images) => {
        const groups = {};

        images.forEach(image => {
            if (!image.uploaded_at) {
                if (!groups['Older Images']) groups['Older Images'] = [];
                groups['Older Images'].push(image);
                return;
            }

            const date = new Date(image.uploaded_at);
            const today = new Date();
            const yesterday = new Date(today);
            yesterday.setDate(yesterday.getDate() - 1);

            let dateKey;
            if (date.toDateString() === today.toDateString()) {
                dateKey = 'Today';
            } else if (date.toDateString() === yesterday.toDateString()) {
                dateKey = 'Yesterday';
            } else {
                dateKey = date.toLocaleDateString('en-US', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
            }

            if (!groups[dateKey]) groups[dateKey] = [];
            groups[dateKey].push(image);
        });

        return groups;
    };

    const imageGroups = groupImagesByDate(images);

    return (
        <div className="gallery">
            {/* Toolbar */}
            <div className="gallery-toolbar">
                <div className="toolbar-left">
                    <h2>Gallery</h2>
                    <span className="image-count">{images.length} images</span>
                </div>

                <div className="toolbar-right">
                    {selectMode && (
                        <>
                            <button className="btn btn-outline" onClick={selectAll}>
                                Select All
                            </button>
                            <button className="btn btn-outline" onClick={deselectAll}>
                                Deselect All
                            </button>
                        </>
                    )}

                    <button
                        className={`btn ${selectMode ? 'btn-secondary' : 'btn-outline'}`}
                        onClick={toggleSelectMode}
                    >
                        {selectMode ? 'Cancel' : 'Select'}
                    </button>

                    <label className="btn btn-primary upload-btn">
                        <svg viewBox="0 0 24 24" fill="none">
                            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke="currentColor" strokeWidth="2" />
                        </svg>
                        Upload
                        <input
                            type="file"
                            multiple
                            accept="image/*"
                            onChange={handleUpload}
                            style={{ display: 'none' }}
                        />
                    </label>
                </div>
            </div>

            {/* Floating Action Bar - Shows when images are selected */}
            {selectMode && selectedImages.size > 0 && (
                <div className="floating-action-bar">
                    <div className="action-bar-content">
                        <span className="selected-count">
                            {selectedImages.size} image{selectedImages.size > 1 ? 's' : ''} selected
                        </span>
                        <button className="btn btn-danger" onClick={handleDelete}>
                            <svg viewBox="0 0 24 24" fill="none">
                                <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" stroke="currentColor" strokeWidth="2" />
                            </svg>
                            Delete
                        </button>
                    </div>
                </div>
            )}

            {/* Gallery Grid with Date Groups */}
            {loading ? (
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading gallery...</p>
                </div>
            ) : images.length === 0 ? (
                <div className="empty-state">
                    <svg viewBox="0 0 24 24" fill="none">
                        <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2" />
                        <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" />
                        <path d="M21 15l-5-5L5 21" stroke="currentColor" strokeWidth="2" />
                    </svg>
                    <h3>No images yet</h3>
                    <p>Upload your first image to get started</p>
                </div>
            ) : (
                <>
                    {Object.entries(imageGroups).map(([dateLabel, groupImages]) => (
                        <div key={dateLabel} className="date-group">
                            <h3 className="date-header">{dateLabel}</h3>
                            <div className="gallery-grid">
                                {groupImages.map((image) => (
                                    <div
                                        key={image.id}
                                        onClick={() => {
                                            if (selectMode) {
                                                toggleImageSelection(image.id);
                                            } else {
                                                setSelectedImage(image);
                                            }
                                        }}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <ImageCard
                                            image={image}
                                            selectMode={selectMode}
                                            isSelected={selectedImages.has(image.id)}
                                            onToggleSelect={() => toggleImageSelection(image.id)}
                                        />
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </>
            )}

            {/* Lightbox Modal */}
            {selectedImage && !selectMode && (
                <div
                    className="lightbox-modal"
                    onClick={() => setSelectedImage(null)}
                    style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        background: 'rgba(0, 0, 0, 0.9)',
                        zIndex: 9999,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '20px'
                    }}
                >
                    {/* Close Button */}
                    <button
                        onClick={() => setSelectedImage(null)}
                        style={{
                            position: 'absolute',
                            top: '20px',
                            right: '20px',
                            background: 'rgba(255, 255, 255, 0.1)',
                            border: 'none',
                            color: 'white',
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            cursor: 'pointer',
                            fontSize: '24px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            zIndex: 10001
                        }}
                    >
                        ×
                    </button>

                    {/* Image Container */}
                    <div
                        onClick={(e) => e.stopPropagation()}
                        style={{
                            position: 'relative',
                            maxWidth: '95%',
                            maxHeight: '90%',
                            display: 'flex',
                            gap: '40px',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        {/* Left: Image */}
                        <img
                            src={`http://localhost:8000${selectedImage.url}`}
                            alt="Full size"
                            style={{
                                maxWidth: selectedImage.description ? '55%' : '100%',
                                maxHeight: '85vh',
                                objectFit: 'contain',
                                borderRadius: '8px',
                                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
                            }}
                        />

                        {/* Right: Description and Download Button */}
                        {selectedImage.description && (
                            <div style={{
                                flex: '1',
                                maxWidth: '400px',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '16px',
                                paddingTop: '20px'
                            }}>
                                {/* Description Box */}
                                <div style={{
                                    background: 'rgba(0, 0, 0, 0.75)',
                                    backdropFilter: 'blur(10px)',
                                    color: 'white',
                                    padding: '20px',
                                    borderRadius: '8px',
                                    fontSize: '0.9rem',
                                    lineHeight: '1.6',
                                    textAlign: 'left',
                                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
                                }}>
                                    <div style={{
                                        fontSize: '0.75rem',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.5px',
                                        color: 'rgba(255, 255, 255, 0.6)',
                                        marginBottom: '8px',
                                        fontWeight: '600'
                                    }}>
                                        Description
                                    </div>
                                    {selectedImage.description}
                                </div>

                                {/* People/Faces Section */}
                                {selectedImage.faces && selectedImage.faces.length > 0 && (
                                    <div style={{
                                        background: 'rgba(0, 0, 0, 0.75)',
                                        backdropFilter: 'blur(10px)',
                                        color: 'white',
                                        padding: '20px',
                                        borderRadius: '8px',
                                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
                                    }}>
                                        <div style={{
                                            fontSize: '0.75rem',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px',
                                            color: 'rgba(255, 255, 255, 0.6)',
                                            marginBottom: '12px',
                                            fontWeight: '600'
                                        }}>
                                            People in this image
                                        </div>
                                        <div style={{
                                            display: 'flex',
                                            flexWrap: 'wrap',
                                            gap: '8px'
                                        }}>
                                            {selectedImage.faces.map((faceName, index) => (
                                                <span
                                                    key={index}
                                                    style={{
                                                        background: 'rgba(59, 130, 246, 0.2)',
                                                        border: '1px solid rgba(59, 130, 246, 0.5)',
                                                        color: 'rgba(147, 197, 253, 1)',
                                                        padding: '6px 12px',
                                                        borderRadius: '16px',
                                                        fontSize: '0.85rem',
                                                        fontWeight: '500'
                                                    }}
                                                >
                                                    {faceName}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Download Button */}
                                <button
                                    onClick={async (e) => {
                                        e.stopPropagation();

                                        try {
                                            // Fetch the image as a blob to force download
                                            const response = await fetch(`http://localhost:8000${selectedImage.url}?download=1`);
                                            if (!response.ok) throw new Error('Download failed');
                                            const blob = await response.blob();

                                            // Create blob URL and download
                                            const blobUrl = window.URL.createObjectURL(blob);
                                            const link = document.createElement('a');
                                            link.href = blobUrl;
                                            link.download = `image-${selectedImage.id}.jpg`;
                                            document.body.appendChild(link);
                                            link.click();
                                            document.body.removeChild(link);

                                            // Clean up blob URL
                                            setTimeout(() => window.URL.revokeObjectURL(blobUrl), 100);
                                        } catch (error) {
                                            console.error('Download failed:', error);
                                            // Fallback: open in new tab
                                            window.open(`http://localhost:8000${selectedImage.url}`, '_blank');
                                        }
                                    }}
                                    className="btn btn-primary"
                                    style={{
                                        padding: '12px 24px',
                                        background: 'rgba(59, 130, 246, 0.9)',
                                        border: 'none',
                                        borderRadius: '8px',
                                        color: 'white',
                                        cursor: 'pointer',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '8px',
                                        transition: 'all 0.2s',
                                        boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)'
                                    }}
                                    onMouseEnter={(e) => {
                                        e.target.style.background = 'rgba(59, 130, 246, 1)';
                                        e.target.style.transform = 'translateY(-2px)';
                                        e.target.style.boxShadow = '0 6px 16px rgba(59, 130, 246, 0.4)';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.target.style.background = 'rgba(59, 130, 246, 0.9)';
                                        e.target.style.transform = 'translateY(0)';
                                        e.target.style.boxShadow = '0 4px 12px rgba(59, 130, 246, 0.3)';
                                    }}
                                >
                                    <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
                                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                    </svg>
                                    Download Image
                                </button>
                            </div>
                        )}

                        {/* If no description, show faces and download button below image */}
                        {!selectedImage.description && (
                            <div style={{
                                position: 'absolute',
                                bottom: selectedImage.faces && selectedImage.faces.length > 0 ? '-140px' : '-60px',
                                left: '50%',
                                transform: 'translateX(-50%)',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '16px',
                                alignItems: 'center'
                            }}>
                                {/* Faces for images without description */}
                                {selectedImage.faces && selectedImage.faces.length > 0 && (
                                    <div style={{
                                        background: 'rgba(0, 0, 0, 0.75)',
                                        backdropFilter: 'blur(10px)',
                                        color: 'white',
                                        padding: '16px 20px',
                                        borderRadius: '8px',
                                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                                        minWidth: '300px'
                                    }}>
                                        <div style={{
                                            fontSize: '0.75rem',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px',
                                            color: 'rgba(255, 255, 255, 0.6)',
                                            marginBottom: '12px',
                                            fontWeight: '600',
                                            textAlign: 'center'
                                        }}>
                                            People in this image
                                        </div>
                                        <div style={{
                                            display: 'flex',
                                            flexWrap: 'wrap',
                                            gap: '8px',
                                            justifyContent: 'center'
                                        }}>
                                            {selectedImage.faces.map((faceName, index) => (
                                                <span
                                                    key={index}
                                                    style={{
                                                        background: 'rgba(59, 130, 246, 0.2)',
                                                        border: '1px solid rgba(59, 130, 246, 0.5)',
                                                        color: 'rgba(147, 197, 253, 1)',
                                                        padding: '6px 12px',
                                                        borderRadius: '16px',
                                                        fontSize: '0.85rem',
                                                        fontWeight: '500'
                                                    }}
                                                >
                                                    {faceName}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                <button
                                    onClick={async (e) => {
                                        e.stopPropagation();

                                        try {
                                            const response = await fetch(`http://localhost:8000${selectedImage.url}?download=1`);
                                            if (!response.ok) throw new Error('Download failed');
                                            const blob = await response.blob();
                                            const blobUrl = window.URL.createObjectURL(blob);
                                            const link = document.createElement('a');
                                            link.href = blobUrl;
                                            link.download = `image-${selectedImage.id}.jpg`;
                                            document.body.appendChild(link);
                                            link.click();
                                            document.body.removeChild(link);
                                            setTimeout(() => window.URL.revokeObjectURL(blobUrl), 100);
                                        } catch (error) {
                                            console.error('Download failed:', error);
                                            window.open(`http://localhost:8000${selectedImage.url}`, '_blank');
                                        }
                                    }}
                                    className="btn btn-primary"
                                    style={{
                                        padding: '12px 24px',
                                        background: 'rgba(59, 130, 246, 0.9)',
                                        border: 'none',
                                        borderRadius: '8px',
                                        color: 'white',
                                        cursor: 'pointer',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px',
                                        boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)'
                                    }}
                                >
                                    <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
                                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                    </svg>
                                    Download Image
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Toast Notification */}
            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    duration={toast.duration}
                    onClose={closeToast}
                />
            )}
        </div>
    );
}

export default Gallery;
