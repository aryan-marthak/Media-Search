import client from './client'

export const searchApi = {
    async normalSearch(query, topK = 20) {
        const response = await client.get('/search/normal', {
            params: { q: query, top_k: topK }
        })
        return response.data
    },

    async deepSearch(query, topK = 20) {
        const response = await client.get('/search/deep', {
            params: { q: query, top_k: topK }
        })
        return response.data
    }
}
