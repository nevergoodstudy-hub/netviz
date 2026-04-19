/**
 * NetViz TypeScript 类型定义
 */

// ==================== PCAP 相关类型 ====================

/** PCAP 文件解析状态 */
export type ParseStatus = 'pending' | 'parsing' | 'completed' | 'failed'

/** PCAP 文件信息 */
export interface PcapFile {
  id: number
  filename: string
  original_filename: string
  file_size: number
  file_hash: string
  status: ParseStatus
  parse_progress: number
  total_packets: number
  total_bytes: number
  packet_count?: number  // 别名
  start_time: string | null
  end_time: string | null
  duration_seconds: number
  created_at: string
}

/** PCAP 列表响应 */
export interface PcapListResponse {
  items: PcapFile[]
  total: number
}

/** 数据包信息 */
export interface Packet {
  id: number
  packet_number: number
  timestamp: string
  src_mac: string | null
  dst_mac: string | null
  src_ip: string | null
  dst_ip: string | null
  protocol: string | null
  src_port: number | null
  dst_port: number | null
  tcp_flags: string | null
  app_protocol: string | null
  length: number
  payload_length: number
}

/** 连接信息 */
export interface Connection {
  id: number
  src_ip: string
  dst_ip: string
  src_port: number | null
  dst_port: number | null
  protocol: string
  packet_count: number
  byte_count: number
  src_to_dst_packets: number
  dst_to_src_packets: number
  src_to_dst_bytes: number
  dst_to_src_bytes: number
  start_time: string
  end_time: string
  duration_seconds: number
  app_protocol: string | null
  is_encrypted: boolean
  risk_score: number
  src_country: string | null
  dst_country: string | null
  src_lat: number | null
  src_lon: number | null
  dst_lat: number | null
  dst_lon: number | null
}

/** 协议统计 */
export interface ProtocolStats {
  protocol: string
  count: number
  bytes: number
  percentage: number
}

/** PCAP 统计信息 */
export interface PcapStats {
  total_packets: number
  total_bytes: number
  unique_ips: number
  total_connections: number
  protocol_stats?: ProtocolStats[]
}

/** Top 通信者 */
export interface TopTalker {
  ip: string
  packets_sent: number
  packets_received: number
  bytes_sent: number
  bytes_received: number
  connections: number
}

/** 网络拓扑节点 */
export interface TopologyNode {
  id: string
  label: string
  ip: string
  type: 'internal' | 'external' | 'gateway'
  packet_count: number
  byte_count: number
}

/** 网络拓扑边 */
export interface TopologyEdge {
  source: string
  target: string
  packets: number
  bytes: number
  protocol: string
}

/** 网络拓扑 */
export interface NetworkTopology {
  nodes: TopologyNode[]
  edges: TopologyEdge[]
}

// ==================== 分析相关类型 ====================

/** 告警严重级别 */
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical'

/** 告警类型 */
export type AlertType = 
  | 'port_scan'
  | 'suspicious_dns'
  | 'large_transfer'
  | 'suspicious_connection'
  | 'potential_malware'
  | 'brute_force'
  | 'data_exfiltration'

/** 告警信息 */
export interface Alert {
  id: number
  pcap_id: number
  alert_type: AlertType
  type?: string  // 别名
  severity: AlertSeverity
  title: string
  description: string
  source_ip: string | null
  dest_ip: string | null
  source_port: number | null
  dest_port: number | null
  packet_ids: number[]
  detected_at: string
  created_at?: string  // 别名
  mitre_technique?: string
  is_resolved: boolean
  resolution_notes: string | null
}

export interface AnomalyResult {
  type: string
  severity: AlertSeverity
  description: string
  details: Record<string, unknown>
  timestamp: string
}

/** DNS 记录 */
export interface DnsRecord {
  id: number
  query_name: string
  query_type: string
  response_ip: string | null
  ttl: number | null
  timestamp: string
}

/** DNS 分析结果 */
export interface DnsAnalysis {
  records: DnsRecord[]
  top_domains?: Array<{ domain: string; count: number }>
  query_types?: Record<string, number>
}

/** HTTP 事务 */
export interface HttpTransaction {
  id: number
  method: string
  host: string
  uri: string
  status_code: number | null
  content_type: string | null
  content_length: number | null
  user_agent: string | null
  request_time: string
  response_time: string | null
}

/** HTTP 分析结果 */
export interface HttpAnalysis {
  transactions: HttpTransaction[]
  top_hosts?: Array<{ host: string; count: number }>
  methods?: Record<string, number>
  status_codes?: Record<string, number>
}

/** 时间序列数据点 */
export interface TimeSeriesPoint {
  timestamp: string
  packets: number
  bytes: number
}

// ==================== AI 相关类型 ====================

/** AI 提供商 */
export type AIProvider = 'openai' | 'anthropic' | 'ollama' | 'deepseek'

/** AI 提供商状态 */
export interface AIProviderStatus {
  provider: AIProvider
  configured: boolean
  model: string
  status: 'configured' | 'not_configured' | 'local'
}

/** AI 聊天消息 */
export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

/** AI 对话 */
export interface Conversation {
  conversation: {
    id: number
    title: string
    provider: AIProvider
    model: string
  }
  messages: ChatMessage[]
}

export interface ConversationSummary {
  id: number
  title: string
  provider: AIProvider
  model: string
  pcap_file_id: number | null
  message_count: number
  created_at: string
  updated_at: string
}

export interface ConversationListResponse {
  items: ConversationSummary[]
}

/** AI 聊天请求 */
export interface ChatRequest {
  pcap_id: number
  message: string
  conversation_id?: number
  provider?: AIProvider
}

/** AI 聊天响应 */
export interface ChatResponse {
  message: string
  conversation_id: number
  provider: AIProvider
  model: string
  prompt_tokens: number
  completion_tokens: number
}

export interface AIProviderTestResult {
  status: 'success' | 'error'
  message: string
  available_models?: string[]
}

/** AI 分析类型 */
export type AnalysisType = 
  | 'security'
  | 'performance'
  | 'protocol'
  | 'anomaly'
  | 'summary'

// ==================== 设置相关类型 ====================

/** 设置项 */
export interface Setting {
  key: string
  value: string
}

/** AI 提供商配置 */
export interface AIProviderConfig {
  provider: string
  api_key?: string
  base_url?: string
  model?: string
}

/** 系统信息 */
export interface SystemInfo {
  version: string
  app_name?: string
  python_version: string
  platform: string
  pcap_count?: number
  storage_used?: number
  debug_mode?: boolean
}

// ==================== 捕获相关类型 ====================

/** 网络接口 */
export interface NetworkInterface {
  name: string
  description: string
  friendly_name: string
  ips: string[]
  mac: string
}

/** 捕获会话状态 */
export interface CaptureStatus {
  is_capturing: boolean
  session_id: string | null
  interface: string | null
  packet_count: number
  byte_count: number
  start_time: string | null
  duration_seconds: number
}

export interface CaptureCapability {
  available: boolean
  interface_count: number
  message: string
  npcap_download: string
}

export interface CaptureSession {
  id: string
  interface: string
  filter: string | null
  start_time: string
  packet_count: number
  byte_count: number
  is_running: boolean
}

/** 捕获配置 */
export interface CaptureConfig {
  interface: string
  filter?: string
  max_packets?: number
  duration?: number
}

// ==================== API 响应包装类型 ====================

/** 通用 API 响应 */
export interface ApiResponse<T> {
  data: T
  status: number
  statusText: string
}

/** 分页参数 */
export interface PaginationParams {
  limit?: number
  offset?: number
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}
