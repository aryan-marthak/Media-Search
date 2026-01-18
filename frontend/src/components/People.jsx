import { useState, useEffect } from 'react';
import axios from 'axios';
import './People.css';

function People() {
    const [people, setPeople] = useState([]);
    const [loading, setLoading] = useState(true);
    const [labelingPerson, setLabelingPerson] = useState(null);
    const [newName, setNewName] = useState('');
    const [selectedPerson, setSelectedPerson] = useState(null);
    const [personImages, setPersonImages] = useState([]);
    const [selectMode, setSelectMode] = useState(false);
    const [selectedPeople, setSelectedPeople] = useState(new Set());

    useEffect(() => {
        fetchPeople();
    }, []);

    const fetchPeople = async () => {
        try {
            setLoading(true);
            const response = await axios.get('http://localhost:8000/people');
            setPeople(response.data.people);
        } catch (error) {
            console.error('Failed to fetch people:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCluster = async () => {
        try {
            setLoading(true);
            await axios.post('http://localhost:8000/cluster-faces');
            await fetchPeople();
        } catch (error) {
            console.error('Clustering failed:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleLabelPerson = async (personId) => {
        if (!newName.trim()) return;

        try {
            await axios.post(`http://localhost:8000/people/${personId}/label`, {
                name: newName
            });
            setLabelingPerson(null);
            setNewName('');
            await fetchPeople();
        } catch (error) {
            console.error('Failed to label person:', error);
        }
    };

    const handleViewPerson = async (person) => {
        try {
            setSelectedPerson(person);
            const response = await axios.get(`http://localhost:8000/people/${person.id}/images`);
            setPersonImages(response.data.images);
        } catch (error) {
            console.error('Failed to fetch person images:', error);
        }
    };

    const closePersonView = () => {
        setSelectedPerson(null);
        setPersonImages([]);
    };

    const toggleSelectMode = () => {
        setSelectMode(!selectMode);
        setSelectedPeople(new Set());
    };

    const togglePersonSelection = (personId) => {
        const newSelected = new Set(selectedPeople);
        if (newSelected.has(personId)) {
            newSelected.delete(personId);
        } else {
            newSelected.add(personId);
        }
        setSelectedPeople(newSelected);
    };

    const selectAll = () => {
        setSelectedPeople(new Set(people.map(p => p.id)));
    };

    const handleDeleteSelected = async () => {
        if (selectedPeople.size === 0) return;

        if (!confirm(`Delete ${selectedPeople.size} selected people?`)) return;

        try {
            setLoading(true);
            // Delete each selected person
            await Promise.all(
                Array.from(selectedPeople).map(personId =>
                    axios.delete(`http://localhost:8000/people/${personId}`)
                )
            );

            setSelectedPeople(new Set());
            setSelectMode(false);
            await fetchPeople();
        } catch (error) {
            console.error('Failed to delete people:', error);
            alert('Failed to delete some people');
        } finally {
            setLoading(false);
        }
    };

    if (loading && people.length === 0) {
        return (
            <div className="people-page">
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading people...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="people-page">
            {/* Header */}
            <div className="people-header">
                <div className="header-left">
                    <h2>People</h2>
                    <span className="people-count">{people.length} people</span>
                </div>
                <div className="header-actions">
                    {selectMode && (
                        <>
                            <button className="btn btn-secondary" onClick={selectAll}>
                                Select All
                            </button>
                            <button
                                className="btn btn-danger"
                                onClick={handleDeleteSelected}
                                disabled={selectedPeople.size === 0}
                            >
                                Delete ({selectedPeople.size})
                            </button>
                        </>
                    )}
                    <button
                        className={`btn ${selectMode ? 'btn-secondary' : 'btn-primary'}`}
                        onClick={toggleSelectMode}
                    >
                        {selectMode ? 'Cancel' : 'Select'}
                    </button>
                    {!selectMode && (
                        <button className="btn btn-primary" onClick={handleCluster}>
                            <svg viewBox="0 0 24 24" fill="none">
                                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" />
                            </svg>
                            Re-cluster Faces
                        </button>
                    )}
                </div>
            </div>

            {/* People Grid */}
            {people.length === 0 ? (
                <div className="empty-state">
                    <svg viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2" />
                        <path d="M6 21v-2a4 4 0 014-4h4a4 4 0 014 4v2" stroke="currentColor" strokeWidth="2" />
                    </svg>
                    <h3>No people found</h3>
                    <p>Upload images with faces and click "Re-cluster Faces"</p>
                </div>
            ) : (
                <div className="people-grid">
                    {people.map((person) => (
                        <div
                            key={person.id}
                            className={`person-card ${selectedPeople.has(person.id) ? 'selected' : ''}`}
                            onClick={() => selectMode && togglePersonSelection(person.id)}
                            style={{ cursor: selectMode ? 'pointer' : 'default' }}
                        >
                            {selectMode && (
                                <div className="select-checkbox" onClick={(e) => e.stopPropagation()}>
                                    <input
                                        type="checkbox"
                                        checked={selectedPeople.has(person.id)}
                                        onChange={() => { }}
                                    />
                                </div>
                            )}
                            <div
                                className="face-thumbnail"
                                onClick={(e) => {
                                    if (!selectMode) {
                                        e.stopPropagation();
                                        handleViewPerson(person);
                                    }
                                }}
                            >
                                <img
                                    src={`http://localhost:8000${person.representative_face_url}`}
                                    alt={person.name || 'Unknown'}
                                />
                            </div>

                            {labelingPerson === person.id ? (
                                <div className="label-input">
                                    <input
                                        type="text"
                                        placeholder="Enter name..."
                                        value={newName}
                                        onChange={(e) => setNewName(e.target.value)}
                                        onKeyPress={(e) => e.key === 'Enter' && handleLabelPerson(person.id)}
                                        autoFocus
                                    />
                                    <div className="label-input-buttons">
                                        <button onClick={() => handleLabelPerson(person.id)}>✓</button>
                                        <button onClick={() => {
                                            setLabelingPerson(null);
                                            setNewName('');
                                        }}>✕</button>
                                    </div>
                                </div>
                            ) : (
                                <div className="person-info">
                                    <h3 onClick={() => {
                                        setLabelingPerson(person.id);
                                        setNewName(person.name || '');
                                    }}>
                                        {person.name || 'Unknown'}
                                    </h3>
                                    <span className="photo-count">{person.face_count} photos</span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Person Images Modal */}
            {selectedPerson && (
                <div className="modal-overlay" onClick={closePersonView}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>{selectedPerson.name || 'Unknown'}</h2>
                            <button className="close-btn" onClick={closePersonView}>✕</button>
                        </div>
                        <div className="modal-body">
                            <div className="images-grid">
                                {personImages.map((image) => (
                                    <div key={image.id} className="image-item">
                                        <img
                                            src={`http://localhost:8000${image.url}`}
                                            alt="Person"
                                        />
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default People;
