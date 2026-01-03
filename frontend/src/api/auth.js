import client from './client'

export const authApi = {
    async register(username, email, password) {
        const response = await client.post('/auth/register', {
            username,
            email,
            password
        })
        return response.data
    },

    async login(email, password) {
        const response = await client.post('/auth/login', {
            email,
            password
        })
        return response.data
    },

    async getMe() {
        const response = await client.get('/auth/me')
        return response.data
    },

    async refresh(refreshToken) {
        const response = await client.post('/auth/refresh', {
            refresh_token: refreshToken
        })
        return response.data
    }
}
