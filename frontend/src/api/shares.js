import client from './client'

export const sharesApi = {
    async share(imageId, username, permission = 'view') {
        const response = await client.post('/shares/', {
            image_id: imageId,
            shared_with_username: username,
            permission
        })
        return response.data
    },

    async revoke(shareId) {
        await client.delete(`/shares/${shareId}`)
    },

    async getSharesByMe() {
        const response = await client.get('/shares/by-me')
        return response.data
    },

    async getSharesWithMe() {
        const response = await client.get('/shares/with-me')
        return response.data
    }
}
