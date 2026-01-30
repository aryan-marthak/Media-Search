import { useState } from 'react';
import axios from 'axios';
import './Search.css';
import './SearchModal.css';

function Search() {
    const [searchMode, setSearchMode] = useState('normal');
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [correctedQuery, setCorrectedQuery] = useState(null);
    const [didYouMean, setDidYouMean] = useState(null);
    const [suggestions, setSuggestions] = useState([]);
    const [hasSearched, setHasSearched] = useState(false);
    const [selectedImage, setSelectedImage] = useState(null);
    const [imageDetails, setImageDetails] = useState(null);
    const [modalLoading, setModalLoading] = useState(false);

    const handleSearch = async (e, overrideQuery = null) => {
        e?.preventDefault();
        const searchQuery = overrideQuery || query;
        if (!searchQuery.trim()) return;

        setLoading(true);
        setHasSearched(true);
        setCorrectedQuery(null);
        setDidYouMean(null);

        try {
            // Determine endpoint based on search mode
            const endpoint = searchMode === 'deep'
                ? 'http://localhost:8000/deep-search'
                : 'http://localhost:8000/search';

            // For normal search, check spelling first
            let finalQuery = searchQuery;
            if (searchMode === 'normal') {
                const spellResponse = await axios.post('http://localhost:8000/spell-check', {
                    query: searchQuery
                });

                // If spelling was auto-corrected, use corrected query and show notification
                if (spellResponse.data.was_corrected) {
                    finalQuery = spellResponse.data.corrected;
                    setCorrectedQuery(finalQuery);
                }
                // If there's a suggestion but not auto-corrected, show "did you mean"
                else if (spellResponse.data.did_you_mean && spellResponse.data.did_you_mean !== searchQuery) {
                    setDidYouMean(spellResponse.data.did_you_mean);
                }
            }

            // Perform search with final query
            const searchResponse = await axios.post(endpoint, {
                query: finalQuery,
                top_k: 20
            });

            setResults(searchResponse.data.results);

            // Get suggestions if no results (only for normal search)
            if (searchResponse.data.results.length === 0 && searchMode === 'normal') {
                const suggestionsResponse = await axios.get(
                    `http://localhost:8000/search-suggestions?query=${finalQuery}`
                );
                setSuggestions(suggestionsResponse.data.suggestions);
            } else {
                setSuggestions([]);
            }
        } catch (error) {
            console.error('Search failed:', error);
            if (error.response?.status === 503) {
                alert('Deep Search is currently unavailable. The VLM model may not be loaded.');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleSuggestionClick = (suggestion) => {
        setQuery(suggestion);
        setDidYouMean(null);
        setCorrectedQuery(null);
        // Trigger search with new query
        setTimeout(() => {
            handleSearch(null, suggestion);
        }, 100);
    };

    const handleClearSearch = () => {
        setQuery('');
        setResults([]);
        setHasSearched(false);
        setCorrectedQuery(null);
        setDidYouMean(null);
        setSuggestions([]);
    };

    const handleImageClick = async (imageId) => {
        setSelectedImage(imageId);
        setModalLoading(true);

        try {
            const response = await axios.get(`http://localhost:8000/image-details/${imageId}`);
            setImageDetails(response.data);
        } catch (error) {
            console.error('Failed to load image details:', error);
            setImageDetails(null);
        } finally {
            setModalLoading(false);
        }
    };

    const closeModal = () => {
        setSelectedImage(null);
        setImageDetails(null);
    };

    return (
        <div className="search-page">
            {/* Search Header */}
            <div className="search-header">
                <h2>Search Your Images</h2>

                {/* Search Mode Toggle */}
                <div className="search-mode-toggle">
                    <button
                        className={`mode-btn ${searchMode === 'normal' ? 'active' : ''}`}
                        onClick={() => setSearchMode('normal')}
                    >
                        <svg viewBox="0 0 24 24" fill="none">
                            <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />
                            <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" />
                        </svg>
                        Normal Search
                    </button>
                    <button
                        className={`mode-btn ${searchMode === 'deep' ? 'active' : ''}`}
                        onClick={() => setSearchMode('deep')}
                    >
                        <svg viewBox="0 0 24 24" fill="none">
                            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" />
                        </svg>
                        Deep Search
                    </button>
                </div>
            </div>

            {/* Search Form */}
            <form className="search-form" onSubmit={handleSearch}>
                <div className="search-input-wrapper">
                    <svg className="search-icon" viewBox="0 0 24 24" fill="none">
                        <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />
                        <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" />
                    </svg>
                    <input
                        type="text"
                        className="search-input"
                        placeholder={searchMode === 'deep'
                            ? "Try: 'person wearing blue shirt', 'sunset with orange sky'..."
                            : "Search for sunset, car, people..."}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                    {query && (
                        <button
                            type="button"
                            className="clear-btn"
                            onClick={handleClearSearch}
                        >
                            <svg viewBox="0 0 24 24" fill="none">
                                <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" />
                            </svg>
                        </button>
                    )}
                </div>
                <button type="submit" className="btn btn-primary search-btn">
                    Search
                </button>
            </form>

            {/* Spell Correction - Only show if query was auto-corrected */}
            {correctedQuery && !didYouMean && (
                <div className="spell-correction">
                    Showing results for <strong>{correctedQuery}</strong>
                </div>
            )}

            {/* Did You Mean - Only show if there's a suggestion but query wasn't auto-corrected */}
            {didYouMean && !correctedQuery && (
                <div className="did-you-mean">
                    Did you mean <button onClick={() => handleSuggestionClick(didYouMean)}>{didYouMean}</button>?
                </div>
            )}

            {/* Loading State */}
            {loading && (
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Searching...</p>
                </div>
            )}

            {/* Results */}
            {!loading && hasSearched && (
                <>
                    {results.length > 0 ? (
                        <div className="search-results">
                            <div className="results-header">
                                <h3>Results for "{correctedQuery || query}"</h3>
                                <span className="result-count">{results.length} images</span>
                            </div>
                            <div className="results-grid">
                                {results.map((result) => (
                                    <div
                                        key={result.image_id}
                                        className="result-card"
                                        onClick={() => handleImageClick(result.image_id)}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <img
                                            src={`http://localhost:8000${result.image_url}`}
                                            alt="Search result"
                                        />
                                        <div className="score-badge">
                                            {(result.score * 100).toFixed(1)}%
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="no-results">
                            <svg viewBox="0 0 24 24" fill="none">
                                <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />
                                <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" />
                                <path d="M11 8v3M11 14h.01" stroke="currentColor" strokeWidth="2" />
                            </svg>
                            <h3>No results found</h3>
                            <p>Try searching for something else</p>

                            {suggestions.length > 0 && (
                                <div className="suggestions">
                                    <p className="suggestions-label">Try searching for:</p>
                                    <div className="suggestion-chips">
                                        {suggestions.map((suggestion, index) => (
                                            <button
                                                key={index}
                                                className="suggestion-chip"
                                                onClick={() => handleSuggestionClick(suggestion)}
                                            >
                                                {suggestion}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </>
            )}

            {/* Image Details Modal */}
            {selectedImage && (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <button className="modal-close" onClick={closeModal}>×</button>

                        {modalLoading ? (
                            <div className="modal-loading">Loading...</div>
                        ) : imageDetails ? (
                            <>
                                <img
                                    src={`http://localhost:8000${imageDetails.image_url}`}
                                    alt="Full size"
                                    className="modal-image"
                                />

                                {imageDetails.vlm_description && (
                                    <div className="vlm-description">
                                        <h3>Image Description</h3>
                                        <p>{imageDetails.vlm_description}</p>
                                    </div>
                                )}

                                {!imageDetails.vlm_processed && (
                                    <div className="no-vlm-warning">
                                        ⚠️ This image doesn't have a description yet.
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="modal-error">Failed to load image details</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default Search;
