import client from './client'

export const imagesApi = {
    async upload(files) {
        const formData = new FormData()
        files.forEach(file => {
            formData.append('files', file)
        })

        const response = await client.post('/images/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })
        return response.data
    },

    async list(skip = 0, limit = 50) {
        const response = await client.get('/images/', {
            params: { skip, limit }
        })
        return response.data
    },

    async get(imageId) {
        const response = await client.get(`/images/${imageId}`)
        return response.data
    },

    async delete(imageId) {
        await client.delete(`/images/${imageId}`)
    },

    async getStatus(imageId) {
        const response = await client.get(`/images/${imageId}/status`)
        return response.data
    },

    getImageUrl(thumbnailPath) {
        if (!thumbnailPath) return null
        return `http://localhost:8000/static/${thumbnailPath}`
    },

    getFullImageUrl(filePath) {
        if (!filePath) return null
        return `http://localhost:8000/static/${filePath}`
    }
}
