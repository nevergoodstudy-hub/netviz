import axios, { AxiosResponse } from 'axios'
import { getApiBaseUrl } from '@/lib/tauri'
import type {
  PcapFile,
  PcapListResponse,
  PcapStats,
  Packet,
  Connection,
  ProtocolStats,
  TopTalker,
  NetworkTopology,
  Alert,
  AlertSeverity,
  TimeSeriesPoint,
  DnsAnalysis,
  HttpAnalysis,
  AIProvider,
  AIProviderStatus,
  ChatRequest,
  ChatResponse,
  Conversation,
  AIProviderConfig,
  SystemInfo,
  NetworkInterface,
  CaptureStatus,
  CaptureConfig,
  PaginationParams,
} from '@/types'

const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 60000,
})

// PCAP API
export const pcapApi = {
  upload: (file: File, onProgress?: (progress: number) => void): Promise<AxiosResponse<PcapFile>> => {
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
  list: (): Promise<AxiosResponse<PcapListResponse>> => api.get('/pcap/list'),
  get: (id: number): Promise<AxiosResponse<PcapFile>> => api.get(`/pcap/${id}`),
  delete: (id: number): Promise<AxiosResponse<void>> => api.delete(`/pcap/${id}`),
  getPackets: (
    id: number,
    params?: PaginationParams & { protocol?: string }
  ): Promise<AxiosResponse<Packet[]>> => api.get(`/pcap/${id}/packets`, { params }),
  getConnections: (id: number): Promise<AxiosResponse<Connection[]>> =>
    api.get(`/pcap/${id}/connections`),
  getStats: (id: number): Promise<AxiosResponse<PcapStats>> =>
    api.get(`/pcap/${id}/stats`),
  getTopology: (id: number): Promise<AxiosResponse<NetworkTopology>> =>
    api.get(`/pcap/${id}/topology`),
}

// 分析 API
export const analysisApi = {
  getProtocolDistribution: (pcapId: number): Promise<AxiosResponse<ProtocolStats[]>> =>
    api.get(`/analysis/protocol-distribution/${pcapId}`),
  getTimeSeries: (
    pcapId: number,
    interval?: number
  ): Promise<AxiosResponse<TimeSeriesPoint[]>> =>
    api.get(`/analysis/time-series/${pcapId}`, { params: { interval } }),
  getTopTalkers: (
    pcapId: number,
    limit?: number
  ): Promise<AxiosResponse<TopTalker[]>> =>
    api.get(`/analysis/top-talkers/${pcapId}`, { params: { limit } }),
  getDnsAnalysis: (pcapId: number): Promise<AxiosResponse<DnsAnalysis>> =>
    api.get(`/analysis/dns-analysis/${pcapId}`),
  getHttpAnalysis: (pcapId: number): Promise<AxiosResponse<HttpAnalysis>> =>
    api.get(`/analysis/http-analysis/${pcapId}`),
  detectAnomalies: (pcapId: number): Promise<AxiosResponse<Alert[]>> =>
    api.post(`/analysis/detect-anomalies/${pcapId}`),
  getAlerts: (params?: {
    pcap_id?: number
    severity?: AlertSeverity
  }): Promise<AxiosResponse<Alert[]>> => api.get('/analysis/alerts', { params }),
}

// AI API
export const aiApi = {
  chat: (data: ChatRequest): Promise<AxiosResponse<ChatResponse>> =>
    api.post('/ai/chat', data),
  getSummary: (
    pcapId: number,
    provider?: AIProvider
  ): Promise<AxiosResponse<{ summary: string }>> =>
    api.post('/ai/summary', { pcap_id: pcapId, provider }),
  analyze: (
    pcapId: number,
    analysisType: string,
    provider?: AIProvider
  ): Promise<AxiosResponse<{ analysis: string }>> =>
    api.post('/ai/analyze', { pcap_id: pcapId, analysis_type: analysisType, provider }),
  getConversations: (pcapId?: number): Promise<AxiosResponse<Conversation[]>> =>
    api.get('/ai/conversations', { params: { pcap_id: pcapId } }),
  getConversation: (id: number): Promise<AxiosResponse<Conversation>> =>
    api.get(`/ai/conversations/${id}`),
}

// 设置 API
export const settingsApi = {
  getAll: (): Promise<AxiosResponse<Record<string, string>>> => api.get('/settings/'),
  update: (key: string, value: string): Promise<AxiosResponse<{ message: string }>> =>
    api.put('/settings/', { key, value }),
  delete: (key: string): Promise<AxiosResponse<{ message: string }>> =>
    api.delete(`/settings/${key}`),
  getAIProviders: (): Promise<AxiosResponse<AIProviderStatus[]>> =>
    api.get('/settings/ai-providers'),
  configureAIProvider: (data: AIProviderConfig): Promise<AxiosResponse<{ message: string }>> =>
    api.post('/settings/ai-providers', data),
  testAIProvider: (provider: AIProvider): Promise<AxiosResponse<{ success: boolean }>> =>
    api.post(`/settings/ai-providers/${provider}/test`),
  getSystemInfo: (): Promise<AxiosResponse<SystemInfo>> => api.get('/settings/system-info'),
}

// 捕获 API
export const captureApi = {
  getInterfaces: (): Promise<AxiosResponse<NetworkInterface[]>> =>
    api.get('/capture/interfaces'),
  getStatus: (): Promise<AxiosResponse<CaptureStatus>> => api.get('/capture/status'),
  start: (config: CaptureConfig): Promise<AxiosResponse<{ session_id: string }>> =>
    api.post('/capture/start', config),
  stop: (sessionId: string): Promise<AxiosResponse<{ pcap_id: number }>> =>
    api.post(`/capture/stop/${sessionId}`),
}

export default api
