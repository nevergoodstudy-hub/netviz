import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, Square, Trash2, Download, RefreshCw, Wifi, WifiOff, AlertTriangle } from 'lucide-react'
import { toast } from '@/components/ui/Toaster'
import { formatBytes, formatNumber } from '@/lib/utils'
import api from '@/services/api'

interface CaptureSession {
  id: string
  interface: string
  filter: string | null
  start_time: string
  packet_count: number
  byte_count: number
  is_running: boolean
}

interface PacketInfo {
  index: number
  timestamp: string
  length: number
  protocol: string
  src_ip: string | null
  dst_ip: string | null
  src_port: number | null
  dst_port: number | null
  info: string
}

interface InterfaceInfo {
  name: string
  description: string
  friendly_name?: string
  ips?: string[]
  mac?: string
}

// API 函数
const captureApi = {
  check: () => api.get('/capture/check'),
  getInterfaces: () => api.get('/capture/interfaces'),
  getSessions: () => api.get('/capture/sessions'),
  getSession: (id: string) => api.get(`/capture/sessions/${id}`),
  getPackets: (id: string, offset = 0, limit = 100) =>
    api.get(`/capture/sessions/${id}/packets`, { params: { offset, limit } }),
  start: (data: { interface: string; filter?: string; max_packets?: number; save_to_file?: boolean }) =>
    api.post('/capture/start', data),
  stop: (id: string) => api.post(`/capture/stop/${id}`),
  delete: (id: string) => api.delete(`/capture/sessions/${id}`),
}

export default function Capture() {
  const queryClient = useQueryClient()
  const [selectedInterface, setSelectedInterface] = useState('')
  const [filter, setFilter] = useState('')
  const [maxPackets, setMaxPackets] = useState(0)
  const [saveToFile, setSaveToFile] = useState(false)
  const [activeSession, setActiveSession] = useState<string | null>(null)
  const packetsEndRef = useRef<HTMLDivElement>(null)

  // 检查抓包功能
  const { data: captureCheck } = useQuery({
    queryKey: ['capture-check'],
    queryFn: () => captureApi.check().then((r) => r.data),
  })

  // 获取网络接口
  const { data: interfaces } = useQuery({
    queryKey: ['capture-interfaces'],
    queryFn: () => captureApi.getInterfaces().then((r) => r.data),
    enabled: captureCheck?.available,
  })

  // 获取会话列表
  const { data: sessions, refetch: refetchSessions } = useQuery({
    queryKey: ['capture-sessions'],
    queryFn: () => captureApi.getSessions().then((r) => r.data),
    refetchInterval: 2000,
  })

  // 获取活动会话的数据包
  const { data: packets } = useQuery({
    queryKey: ['capture-packets', activeSession],
    queryFn: () => captureApi.getPackets(activeSession!, 0, 500).then((r) => r.data),
    enabled: !!activeSession,
    refetchInterval: activeSession ? 1000 : false,
  })

  // 自动滚动到最新数据包
  useEffect(() => {
    if (packets && packets.length > 0) {
      packetsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [packets?.length])

  // 开始抓包
  const startMutation = useMutation({
    mutationFn: () =>
      captureApi.start({
        interface: selectedInterface,
        filter: filter || undefined,
        max_packets: maxPackets || 0,
        save_to_file: saveToFile,
      }),
    onSuccess: (res) => {
      setActiveSession(res.data.id)
      queryClient.invalidateQueries({ queryKey: ['capture-sessions'] })
      toast({ title: '开始抓包', description: `会话 ${res.data.id}`, type: 'success' })
    },
    onError: (err: Error) => {
      toast({ title: '启动失败', description: err.message, type: 'error' })
    },
  })

  // 停止抓包
  const stopMutation = useMutation({
    mutationFn: (id: string) => captureApi.stop(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['capture-sessions'] })
      toast({ title: '已停止抓包', type: 'success' })
    },
  })

  // 删除会话
  const deleteMutation = useMutation({
    mutationFn: (id: string) => captureApi.delete(id),
    onSuccess: () => {
      if (activeSession === deleteMutation.variables) {
        setActiveSession(null)
      }
      queryClient.invalidateQueries({ queryKey: ['capture-sessions'] })
      toast({ title: '会话已删除', type: 'success' })
    },
  })

  const activeSessionData = sessions?.find((s: CaptureSession) => s.id === activeSession)

  // 如果抓包功能不可用
  if (captureCheck && !captureCheck.available) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">实时抓包</h1>
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <AlertTriangle className="h-6 w-6 text-yellow-500 mt-0.5" />
            <div>
              <h3 className="font-semibold text-yellow-800 dark:text-yellow-200">
                抓包功能不可用
              </h3>
              <p className="text-yellow-700 dark:text-yellow-300 mt-1">
                {captureCheck.message}
              </p>
              <p className="text-sm text-yellow-600 dark:text-yellow-400 mt-2">
                Windows 系统需要安装 Npcap 驱动才能进行网络抓包。
              </p>
              <a
                href={captureCheck.npcap_download}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
              >
                <Download className="h-4 w-4" />
                下载 Npcap
              </a>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Wifi className="h-6 w-6 text-primary" />
          实时抓包
        </h1>
        <button
          onClick={() => refetchSessions()}
          className="p-2 hover:bg-accent rounded-lg"
          title="刷新"
        >
          <RefreshCw className="h-5 w-5" />
        </button>
      </div>

      {/* 抓包控制 */}
      <div className="bg-card border rounded-lg p-4 space-y-4">
        <h2 className="font-semibold">抓包设置</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="text-sm text-muted-foreground">网络接口</label>
            <select
              value={selectedInterface}
              onChange={(e) => setSelectedInterface(e.target.value)}
              className="w-full mt-1 px-3 py-2 border rounded-lg bg-background"
            >
              <option value="">选择接口...</option>
              {interfaces?.map((iface: InterfaceInfo) => (
                <option key={iface.name} value={iface.name}>
                  {iface.friendly_name || iface.description}
                  {iface.ips && iface.ips.length > 0 && ` (${iface.ips[0]})`}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm text-muted-foreground">BPF 过滤器</label>
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="如: tcp port 80"
              className="w-full mt-1 px-3 py-2 border rounded-lg bg-background"
            />
          </div>
          <div>
            <label className="text-sm text-muted-foreground">最大数据包</label>
            <input
              type="number"
              value={maxPackets || ''}
              onChange={(e) => setMaxPackets(parseInt(e.target.value) || 0)}
              placeholder="0 = 无限制"
              className="w-full mt-1 px-3 py-2 border rounded-lg bg-background"
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={saveToFile}
                onChange={(e) => setSaveToFile(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">保存到文件</span>
            </label>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => startMutation.mutate()}
            disabled={!selectedInterface || startMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
          >
            <Play className="h-4 w-4" />
            开始抓包
          </button>
        </div>
      </div>

      {/* 会话列表 */}
      {sessions && sessions.length > 0 && (
        <div className="bg-card border rounded-lg">
          <div className="p-4 border-b">
            <h2 className="font-semibold">抓包会话</h2>
          </div>
          <div className="divide-y">
            {sessions.map((session: CaptureSession) => (
              <div
                key={session.id}
                className={`p-4 flex items-center justify-between cursor-pointer hover:bg-accent/50 ${
                  activeSession === session.id ? 'bg-accent' : ''
                }`}
                onClick={() => setActiveSession(session.id)}
              >
                <div className="flex items-center gap-4">
                  {session.is_running ? (
                    <Wifi className="h-5 w-5 text-green-500 animate-pulse" />
                  ) : (
                    <WifiOff className="h-5 w-5 text-muted-foreground" />
                  )}
                  <div>
                    <div className="font-medium">
                      {session.interface}
                      {session.filter && (
                        <span className="text-sm text-muted-foreground ml-2">
                          ({session.filter})
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {formatNumber(session.packet_count)} 包 · {formatBytes(session.byte_count)}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {session.is_running && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        stopMutation.mutate(session.id)
                      }}
                      className="p-2 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
                      title="停止"
                    >
                      <Square className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      if (confirm('确定删除此会话？')) {
                        deleteMutation.mutate(session.id)
                      }
                    }}
                    className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded"
                    title="删除"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 数据包列表 */}
      {activeSession && (
        <div className="bg-card border rounded-lg">
          <div className="p-4 border-b flex items-center justify-between">
            <h2 className="font-semibold">
              数据包列表
              {activeSessionData?.is_running && (
                <span className="ml-2 text-sm text-green-500 animate-pulse">● 实时</span>
              )}
            </h2>
            <span className="text-sm text-muted-foreground">
              {formatNumber(packets?.length || 0)} / {formatNumber(activeSessionData?.packet_count || 0)}
            </span>
          </div>
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-card">
                <tr className="border-b">
                  <th className="text-left p-2 w-16">#</th>
                  <th className="text-left p-2 w-24">时间</th>
                  <th className="text-left p-2">源地址</th>
                  <th className="text-left p-2">目的地址</th>
                  <th className="text-left p-2 w-20">协议</th>
                  <th className="text-right p-2 w-16">长度</th>
                  <th className="text-left p-2">信息</th>
                </tr>
              </thead>
              <tbody>
                {packets?.map((pkt: PacketInfo) => (
                  <tr
                    key={pkt.index}
                    className={`border-b hover:bg-accent/50 ${
                      pkt.protocol === 'TCP'
                        ? 'bg-blue-50 dark:bg-blue-900/10'
                        : pkt.protocol === 'UDP'
                        ? 'bg-green-50 dark:bg-green-900/10'
                        : pkt.protocol === 'DNS'
                        ? 'bg-yellow-50 dark:bg-yellow-900/10'
                        : pkt.protocol === 'ICMP'
                        ? 'bg-purple-50 dark:bg-purple-900/10'
                        : ''
                    }`}
                  >
                    <td className="p-2 text-muted-foreground">{pkt.index}</td>
                    <td className="p-2 font-mono text-xs">
                      {new Date(pkt.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="p-2 font-mono">
                      {pkt.src_ip}
                      {pkt.src_port && `:${pkt.src_port}`}
                    </td>
                    <td className="p-2 font-mono">
                      {pkt.dst_ip}
                      {pkt.dst_port && `:${pkt.dst_port}`}
                    </td>
                    <td className="p-2">
                      <span
                        className={`px-1.5 py-0.5 text-xs rounded ${
                          pkt.protocol === 'TCP'
                            ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                            : pkt.protocol === 'UDP'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                            : pkt.protocol === 'DNS'
                            ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
                            : pkt.protocol === 'ICMP'
                            ? 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300'
                            : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                        }`}
                      >
                        {pkt.protocol}
                      </span>
                    </td>
                    <td className="p-2 text-right">{pkt.length}</td>
                    <td className="p-2 truncate max-w-xs" title={pkt.info}>
                      {pkt.info}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div ref={packetsEndRef} />
          </div>
        </div>
      )}
    </div>
  )
}
