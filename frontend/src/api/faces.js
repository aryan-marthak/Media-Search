import client from './client'

export const facesApi = {
    async getClusters() {
        const response = await client.get('/faces/clusters')
        return response.data
    },

    async getClusterImages(clusterId) {
        const response = await client.get(`/faces/clusters/${clusterId}/images`)
        return response.data
    },

    async updateClusterName(clusterId, name) {
        const response = await client.put(`/faces/clusters/${clusterId}/name`, { name })
        return response.data
    },

    async searchByPerson(name) {
        const response = await client.get('/faces/search', {
            params: { name }
        })
        return response.data
    }
}
