import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Gallery from './pages/Gallery'
import Search from './pages/Search'
import Faces from './pages/Faces'
import SharedWithMe from './pages/SharedWithMe'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
    const { isAuthenticated, loading } = useAuth()

    if (loading) {
        return (
            <div className="loading-screen">
                <div className="loading-spinner"></div>
                <p>Loading...</p>
            </div>
        )
    }

    return (
        <Routes>
            <Route path="/login" element={
                isAuthenticated ? <Navigate to="/" replace /> : <Login />
            } />
            <Route path="/signup" element={
                isAuthenticated ? <Navigate to="/" replace /> : <Signup />
            } />

            <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                <Route path="/" element={<Gallery />} />
                <Route path="/search" element={<Search />} />
                <Route path="/faces" element={<Faces />} />
                <Route path="/shared" element={<SharedWithMe />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    )
}

export default App
