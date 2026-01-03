import { useState } from 'react'
import { Search as SearchIcon, Zap, Brain, X } from 'lucide-react'
import { searchApi } from '../api/search'
import { imagesApi } from '../api/images'

function Search() {
    const [query, setQuery] = useState('')
    const [mode, setMode] = useState('normal') // 'normal' or 'deep'
    const [results, setResults] = useState([])
    const [loading, setLoading] = useState(false)
    const [searched, setSearched] = useState(false)
    const [selectedImage, setSelectedImage] = useState(null)

    const handleSearch = async (e) => {
        e.preventDefault()
        if (!query.trim()) return

        setLoading(true)
        setSearched(true)

        try {
            const response = mode === 'normal'
                ? await searchApi.normalSearch(query)
                : await searchApi.deepSearch(query)

            setResults(response.results)
        } catch (err) {
            console.error('Search failed:', err)
            setResults([])
        } finally {
            setLoading(false)
        }
    }

    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">Search</h1>
            </div>

            <div className="search-container">
                <form className="search-bar" onSubmit={handleSearch}>
                    <div className="search-input-wrapper">
                        <SearchIcon className="search-icon" size={20} />
                        <input
                            type="text"
                            className="search-input"
                            placeholder="Search your photos... (e.g., 'man walking at night')"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                        />
                    </div>

                    <div className="search-mode-toggle">
                        <button
                            type="button"
                            className={`mode-btn ${mode === 'normal' ? 'active' : ''}`}
                            onClick={() => setMode('normal')}
                            title="Fast embedding-based search"
                        >
                            <Zap size={16} />
                            Fast
                        </button>
                        <button
                            type="button"
                            className={`mode-btn ${mode === 'deep' ? 'active' : ''}`}
                            onClick={() => setMode('deep')}
                            title="Accurate search with VLM validation"
                        >
                            <Brain size={16} />
                            Deep
                        </button>
                    </div>

                    <button type="submit" className="btn btn-primary" disabled={loading}>
                        {loading ? 'Searching...' : 'Search'}
                    </button>
                </form>

                {/* Search mode info */}
                <div style={{
                    textAlign: 'center',
                    color: 'var(--text-muted)',
                    fontSize: '0.875rem',
                    marginBottom: 'var(--spacing-xl)'
                }}>
                    {mode === 'normal' ? (
                        <span>⚡ Fast search uses SigLIP embeddings for quick results</span>
                    ) : (
                        <span>🧠 Deep search uses metadata matching and VLM validation for accurate results</span>
                    )}
                </div>

                {/* Results */}
                {loading ? (
                    <div className="loading-screen" style={{ minHeight: '30vh' }}>
                        <div className="loading-spinner"></div>
                        <p>{mode === 'deep' ? 'Running deep analysis...' : 'Searching...'}</p>
                    </div>
                ) : searched && results.length === 0 ? (
                    <div className="empty-state">
                        <SearchIcon className="empty-state-icon" />
                        <h3>No results found</h3>
                        <p>Try a different search query or use Deep search for better accuracy</p>
                    </div>
                ) : results.length > 0 ? (
                    <>
                        <div style={{
                            marginBottom: 'var(--spacing-md)',
                            color: 'var(--text-secondary)',
                            fontSize: '0.875rem'
                        }}>
                            Found {results.length} results for "{query}"
                        </div>
                        <div className="image-grid">
                            {results.map((result) => (
                                <div
                                    key={result.id}
                                    className="image-card"
                                    onClick={() => setSelectedImage(result)}
                                >
                                    <img
                                        src={imagesApi.getImageUrl(result.thumbnail_path)}
                                        alt={result.filename}
                                        loading="lazy"
                                    />
                                    <div className="image-card-overlay">
                                        <div>
                                            <div style={{ color: 'white', fontSize: '0.875rem' }}>
                                                {result.filename}
                                            </div>
                                            <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                                                Score: {(result.score * 100).toFixed(1)}%
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </>
                ) : null}
            </div>

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
                    {selectedImage.metadata && (
                        <div style={{
                            position: 'absolute',
                            bottom: 'var(--spacing-xl)',
                            left: '50%',
                            transform: 'translateX(-50%)',
                            background: 'var(--bg-card)',
                            padding: 'var(--spacing-md)',
                            borderRadius: 'var(--radius-lg)',
                            backdropFilter: 'blur(10px)',
                            maxWidth: '90vw'
                        }}>
                            <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                                {selectedImage.metadata.caption || 'No description'}
                            </div>
                            <div style={{
                                display: 'flex',
                                gap: 'var(--spacing-sm)',
                                marginTop: 'var(--spacing-sm)',
                                flexWrap: 'wrap'
                            }}>
                                {selectedImage.metadata.objects?.map((obj, i) => (
                                    <span
                                        key={i}
                                        style={{
                                            background: 'var(--accent-gradient)',
                                            padding: '2px 8px',
                                            borderRadius: 'var(--radius-sm)',
                                            fontSize: '0.75rem'
                                        }}
                                    >
                                        {obj}
                                    </span>
                                ))}
                                {selectedImage.metadata.action && (
                                    <span style={{
                                        background: 'rgba(34, 197, 94, 0.2)',
                                        color: 'var(--success)',
                                        padding: '2px 8px',
                                        borderRadius: 'var(--radius-sm)',
                                        fontSize: '0.75rem'
                                    }}>
                                        {selectedImage.metadata.action}
                                    </span>
                                )}
                                {selectedImage.metadata.time && (
                                    <span style={{
                                        background: 'rgba(59, 130, 246, 0.2)',
                                        color: '#3b82f6',
                                        padding: '2px 8px',
                                        borderRadius: 'var(--radius-sm)',
                                        fontSize: '0.75rem'
                                    }}>
                                        {selectedImage.metadata.time}
                                    </span>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default Search
