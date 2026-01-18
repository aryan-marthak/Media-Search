import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Gallery from './components/Gallery';
import Search from './components/Search';
import People from './components/People';
import './App.css';

function AppContent() {
    const location = useLocation();
    const [activeTab, setActiveTab] = useState('gallery');

    // Sync activeTab with current route
    useEffect(() => {
        const path = location.pathname;
        if (path === '/') setActiveTab('gallery');
        else if (path === '/search') setActiveTab('search');
        else if (path === '/people') setActiveTab('people');
    }, [location]);

    return (
        <div className="app">
            {/* Header */}
            <header className="header">
                <div className="header-content">
                    <div className="logo">
                        <svg className="logo-icon" viewBox="0 0 24 24" fill="none">
                            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" stroke="currentColor" strokeWidth="2" />
                            <circle cx="12" cy="13" r="4" stroke="currentColor" strokeWidth="2" />
                        </svg>
                        <h1>PIXEL SNAP</h1>
                    </div>

                    <nav className="nav-tabs">
                        <Link
                            to="/"
                            className={`nav-tab ${activeTab === 'gallery' ? 'active' : ''}`}
                            onClick={() => setActiveTab('gallery')}
                        >
                            <svg viewBox="0 0 24 24" fill="none">
                                <rect x="3" y="3" width="7" height="7" stroke="currentColor" strokeWidth="2" />
                                <rect x="14" y="3" width="7" height="7" stroke="currentColor" strokeWidth="2" />
                                <rect x="3" y="14" width="7" height="7" stroke="currentColor" strokeWidth="2" />
                                <rect x="14" y="14" width="7" height="7" stroke="currentColor" strokeWidth="2" />
                            </svg>
                            Gallery
                        </Link>
                        <Link
                            to="/search"
                            className={`nav-tab ${activeTab === 'search' ? 'active' : ''}`}
                            onClick={() => setActiveTab('search')}
                        >
                            <svg viewBox="0 0 24 24" fill="none">
                                <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />
                                <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" />
                            </svg>
                            Search
                        </Link>
                        <Link
                            to="/people"
                            className={`nav-tab ${activeTab === 'people' ? 'active' : ''}`}
                            onClick={() => setActiveTab('people')}
                        >
                            <svg viewBox="0 0 24 24" fill="none">
                                <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2" />
                                <path d="M6 21v-2a4 4 0 014-4h4a4 4 0 014 4v2" stroke="currentColor" strokeWidth="2" />
                            </svg>
                            People
                        </Link>
                    </nav>
                </div>
            </header>

            {/* Main Content */}
            <main className="main-content">
                <Routes>
                    <Route path="/" element={<Gallery />} />
                    <Route path="/search" element={<Search />} />
                    <Route path="/people" element={<People />} />
                </Routes>
            </main>
        </div>
    );
}

function App() {
    return (
        <Router>
            <AppContent />
        </Router>
    );
}

export default App;
