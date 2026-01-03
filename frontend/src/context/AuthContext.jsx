import { createContext, useContext, useState, useEffect } from 'react'
import { authApi } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        checkAuth()
    }, [])

    const checkAuth = async () => {
        const token = localStorage.getItem('access_token')
        if (!token) {
            setLoading(false)
            return
        }

        try {
            const userData = await authApi.getMe()
            setUser(userData)
        } catch (err) {
            // Token invalid or expired
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
        } finally {
            setLoading(false)
        }
    }

    const login = async (email, password) => {
        try {
            setError(null)
            const tokens = await authApi.login(email, password)
            localStorage.setItem('access_token', tokens.access_token)
            localStorage.setItem('refresh_token', tokens.refresh_token)

            const userData = await authApi.getMe()
            setUser(userData)
            return true
        } catch (err) {
            setError(err.response?.data?.detail || 'Login failed')
            return false
        }
    }

    const signup = async (username, email, password) => {
        try {
            setError(null)
            await authApi.register(username, email, password)
            // Auto-login after signup
            return await login(email, password)
        } catch (err) {
            setError(err.response?.data?.detail || 'Registration failed')
            return false
        }
    }

    const logout = () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setUser(null)
    }

    const value = {
        user,
        loading,
        error,
        isAuthenticated: !!user,
        token: localStorage.getItem('access_token'),
        login,
        signup,
        logout,
        clearError: () => setError(null)
    }

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
