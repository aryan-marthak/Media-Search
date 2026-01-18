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
                                    <ImageCard
                                        key={image.id}
                                        image={image}
                                        selectMode={selectMode}
                                        isSelected={selectedImages.has(image.id)}
                                        onToggleSelect={() => toggleImageSelection(image.id)}
                                    />
                                ))}
                            </div>
                        </div>
                    ))}
                </>
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
