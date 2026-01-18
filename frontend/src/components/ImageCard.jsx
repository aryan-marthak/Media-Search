import './ImageCard.css';

function ImageCard({ image, selectMode, isSelected, onToggleSelect }) {
    return (
        <div className={`image-card ${isSelected ? 'selected' : ''}`}>
            {selectMode && (
                <div className="select-overlay" onClick={onToggleSelect}>
                    <div className={`checkbox ${isSelected ? 'checked' : ''}`}>
                        {isSelected && (
                            <svg viewBox="0 0 24 24" fill="none">
                                <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="3" />
                            </svg>
                        )}
                    </div>
                </div>
            )}

            <img
                src={`http://localhost:8000${image.url}`}
                alt="Gallery image"
            />
        </div>
    );
}

export default ImageCard;
