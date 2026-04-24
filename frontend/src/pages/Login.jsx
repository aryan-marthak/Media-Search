import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Mail, Lock, Eye, EyeOff, GalleryVerticalEnd } from 'lucide-react'

function Login() {
    const { login, error, clearError, isAuthenticated, loading: authLoading } = useAuth()
    const navigate = useNavigate()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [loading, setLoading] = useState(false)

    // Redirect if already logged in
    useEffect(() => {
        if (!authLoading && isAuthenticated) navigate('/', { replace: true })
    }, [isAuthenticated, authLoading, navigate])

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        const ok = await login(email, password)
        setLoading(false)
        if (ok) navigate('/', { replace: true })
    }

    return (
        <div className="auth-page">
            <div className="auth-header">
                <Link to="/" className="auth-logo-brand">
                    <div className="auth-logo-icon">
                        <GalleryVerticalEnd size={16} className="logo-icon" />
                    </div>
                    Pixelsnap
                </Link>
            </div>
            <div className="auth-frame">
                <div className="auth-frame-inner">
                <div className="auth-form-side">
                    <div className="auth-card">
                        <div className="auth-logo-titles">
                            <h1>Welcome Back</h1>
                            <p>Sign in to your account</p>
                        </div>

                        {error && (
                            <div className="auth-error" onClick={clearError}>
                                {error}
                            </div>
                        )}

                        <form className="auth-form" onSubmit={handleSubmit}>
                            <div className="input-group">
                                <label htmlFor="email">Email</label>
                                <div style={{ position: 'relative' }}>
                                    <input
                                        id="email"
                                        type="email"
                                        className="input"
                                        placeholder="you@example.com"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                        style={{ paddingLeft: '40px', width: '100%' }}
                                    />
                                    <Mail
                                        size={18}
                                        style={{
                                            position: 'absolute',
                                            left: '12px',
                                            top: '50%',
                                            transform: 'translateY(-50%)',
                                            color: 'var(--text-muted)'
                                        }}
                                    />
                                </div>
                            </div>

                            <div className="input-group">
                                <label htmlFor="password">Password</label>
                                <div style={{ position: 'relative' }}>
                                    <input
                                        id="password"
                                        type={showPassword ? 'text' : 'password'}
                                        className="input"
                                        placeholder="••••••••"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                        style={{ paddingLeft: '40px', paddingRight: '40px', width: '100%' }}
                                    />
                                    <Lock
                                        size={18}
                                        style={{
                                            position: 'absolute',
                                            left: '12px',
                                            top: '50%',
                                            transform: 'translateY(-50%)',
                                            color: 'var(--text-muted)'
                                        }}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        style={{
                                            position: 'absolute',
                                            right: '12px',
                                            top: '50%',
                                            transform: 'translateY(-50%)',
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer',
                                            color: 'var(--text-muted)'
                                        }}
                                    >
                                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                    </button>
                                </div>
                            </div>

                            <button
                                type="submit"
                                className="btn btn-primary"
                                disabled={loading}
                            >
                                {loading ? 'Signing in...' : 'Sign In'}
                            </button>
                        </form>

                        <div className="auth-divider">or</div>

                        <p className="auth-footer">
                            Don't have an account? <Link to="/signup">Sign up</Link>
                        </p>
                    </div>
                </div>
                <div className="auth-image-side">
                    <img
                        src="/app.png"
                        alt="App Showcase"
                    />
                </div>
                </div>
            </div>
        </div>
    )
}

export default Login
