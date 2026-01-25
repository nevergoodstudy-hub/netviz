import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// PCAP API
export const pcapApi = {
  upload: (file: File, onProgress?: (progress: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/pcap/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total))
        }
      },
    })
  },
  list: () => api.get('/pcap/'),
  get: (id: number) => api.get(`/pcap/${id}`),
  delete: (id: number) => api.delete(`/pcap/${id}`),
  getPackets: (id: number, params?: { limit?: number; offset?: number; protocol?: string }) =>
    api.get(`/pcap/${id}/packets`, { params }),
  getConnections: (id: number) => api.get(`/pcap/${id}/connections`),
  getStats: (id: number) => api.get(`/pcap/${id}/stats`),
  getTopology: (id: number) => api.get(`/pcap/${id}/topology`),
}

// 分析 API
export const analysisApi = {
  getProtocolDistribution: (pcapId: number) =>
    api.get(`/analysis/protocol-distribution/${pcapId}`),
  getTimeSeries: (pcapId: number, interval?: number) =>
    api.get(`/analysis/time-series/${pcapId}`, { params: { interval } }),
  getTopTalkers: (pcapId: number, limit?: number) =>
    api.get(`/analysis/top-talkers/${pcapId}`, { params: { limit } }),
  getDnsAnalysis: (pcapId: number) => api.get(`/analysis/dns-analysis/${pcapId}`),
  getHttpAnalysis: (pcapId: number) => api.get(`/analysis/http-analysis/${pcapId}`),
  detectAnomalies: (pcapId: number) => api.post(`/analysis/detect-anomalies/${pcapId}`),
  getAlerts: (params?: { pcap_id?: number; severity?: string }) =>
    api.get('/analysis/alerts', { params }),
}

// AI API
export const aiApi = {
  chat: (data: { pcap_id: number; message: string; conversation_id?: number; provider?: string }) =>
    api.post('/ai/chat', data),
  getSummary: (pcapId: number, provider?: string) =>
    api.post('/ai/summary', { pcap_id: pcapId, provider }),
  analyze: (pcapId: number, analysisType: string, provider?: string) =>
    api.post('/ai/analyze', { pcap_id: pcapId, analysis_type: analysisType, provider }),
  getConversations: (pcapId?: number) =>
    api.get('/ai/conversations', { params: { pcap_id: pcapId } }),
  getConversation: (id: number) => api.get(`/ai/conversations/${id}`),
}

// 设置 API
export const settingsApi = {
  getAll: () => api.get('/settings/'),
  update: (key: string, value: string) => api.put('/settings/', { key, value }),
  delete: (key: string) => api.delete(`/settings/${key}`),
  getAIProviders: () => api.get('/settings/ai-providers'),
  configureAIProvider: (data: { provider: string; api_key?: string; base_url?: string; model?: string }) =>
    api.post('/settings/ai-providers', data),
  testAIProvider: (provider: string) => api.post(`/settings/ai-providers/${provider}/test`),
  getSystemInfo: () => api.get('/settings/system-info'),
}

export default api
