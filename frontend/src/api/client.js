import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const client = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json'
    }
})

// Request interceptor to add auth token
client.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// Response interceptor to handle token refresh
client.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config

        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true

            const refreshToken = localStorage.getItem('refresh_token')
            if (refreshToken) {
                try {
                    const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
                        refresh_token: refreshToken
                    })

                    const { access_token, refresh_token } = response.data
                    localStorage.setItem('access_token', access_token)
                    localStorage.setItem('refresh_token', refresh_token)

                    originalRequest.headers.Authorization = `Bearer ${access_token}`
                    return client(originalRequest)
                } catch (refreshError) {
                    // Refresh failed, logout
                    localStorage.removeItem('access_token')
                    localStorage.removeItem('refresh_token')
                    window.location.href = '/login'
                }
            }
        }

        return Promise.reject(error)
    }
)

export default client
