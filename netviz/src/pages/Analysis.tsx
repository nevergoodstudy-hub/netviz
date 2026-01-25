import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { AlertTriangle, Search, Loader2 } from 'lucide-react'
import { pcapApi, analysisApi } from '@/services/api'
import { toast } from '@/components/ui/Toaster'

export default function Analysis() {
  const [selectedPcap, setSelectedPcap] = useState<number | null>(null)

  const { data: pcapList } = useQuery({
    queryKey: ['pcap-list'],
    queryFn: () => pcapApi.list().then((r) => r.data),
  })

  const { data: alerts } = useQuery({
    queryKey: ['alerts', selectedPcap],
    queryFn: () => analysisApi.getAlerts({ pcap_id: selectedPcap || undefined }).then((r) => r.data),
  })

  const { data: dnsAnalysis } = useQuery({
    queryKey: ['dns-analysis', selectedPcap],
    queryFn: () => analysisApi.getDnsAnalysis(selectedPcap!).then((r) => r.data),
    enabled: !!selectedPcap,
  })

  const { data: httpAnalysis } = useQuery({
    queryKey: ['http-analysis', selectedPcap],
    queryFn: () => analysisApi.getHttpAnalysis(selectedPcap!).then((r) => r.data),
    enabled: !!selectedPcap,
  })

  const detectMutation = useMutation({
    mutationFn: () => analysisApi.detectAnomalies(selectedPcap!),
    onSuccess: (res) => {
      const count = res.data.length
      toast({
        title: '异常检测完成',
        description: `发现 ${count} 个可疑行为`,
        type: count > 0 ? 'warning' : 'success',
      })
    },
    onError: () => {
      toast({ title: '检测失败', type: 'error' })
    },
  })

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">流量分析</h1>
        <div className="flex items-center gap-4">
          <select
            value={selectedPcap || ''}
            onChange={(e) => setSelectedPcap(e.target.value ? parseInt(e.target.value) : null)}
            className="px-3 py-2 border rounded-lg bg-background"
          >
            <option value="">选择 PCAP 文件</option>
            {pcapList?.items?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.original_filename}
              </option>
            ))}
          </select>
          {selectedPcap && (
            <button
              onClick={() => detectMutation.mutate()}
              disabled={detectMutation.isPending}
              className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 disabled:opacity-50"
            >
              {detectMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              异常检测
            </button>
          )}
        </div>
      </div>

      {/* 告警列表 */}
      <div className="bg-card border rounded-lg">
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="font-semibold">告警列表</h2>
          <span className="text-sm text-muted-foreground">{alerts?.length || 0} 条告警</span>
        </div>
        {alerts && alerts.length > 0 ? (
          <div className="divide-y">
            {alerts.map((alert) => (
              <div key={alert.id} className="p-4 flex items-start gap-4">
                <AlertTriangle
                  className={`h-5 w-5 mt-0.5 ${
                    alert.severity === 'high'
                      ? 'text-red-500'
                      : alert.severity === 'medium'
                      ? 'text-yellow-500'
                      : 'text-blue-500'
                  }`}
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{alert.title}</span>
                    <span
                      className={`px-2 py-0.5 text-xs rounded-full ${
                        alert.severity === 'high'
                          ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                          : alert.severity === 'medium'
                          ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
                          : 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                      }`}
                    >
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">{alert.description}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                    {alert.source_ip && <span>源: {alert.source_ip}</span>}
                    {alert.dest_ip && <span>目标: {alert.dest_ip}</span>}
                    {alert.mitre_technique && <span>MITRE: {alert.mitre_technique}</span>}
                    <span>{new Date(alert.detected_at).toLocaleString('zh-CN')}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-muted-foreground">暂无告警</div>
        )}
      </div>

      {/* DNS 和 HTTP 分析 */}
      {selectedPcap && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* DNS 分析 */}
          <div className="bg-card border rounded-lg">
            <div className="p-4 border-b">
              <h2 className="font-semibold">DNS 分析</h2>
            </div>
            {dnsAnalysis ? (
              <div className="p-4 space-y-4">
                <div>
                  <h4 className="text-sm font-medium mb-2">Top 域名</h4>
                  <div className="space-y-1">
                    {dnsAnalysis.top_domains?.slice(0, 10).map((d: { domain: string; count: number }) => (
                      <div key={d.domain} className="flex justify-between text-sm">
                        <span className="font-mono truncate">{d.domain}</span>
                        <span className="text-muted-foreground">{d.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-muted-foreground">暂无 DNS 数据</div>
            )}
          </div>

          {/* HTTP 分析 */}
          <div className="bg-card border rounded-lg">
            <div className="p-4 border-b">
              <h2 className="font-semibold">HTTP 分析</h2>
            </div>
            {httpAnalysis ? (
              <div className="p-4 space-y-4">
                <div>
                  <h4 className="text-sm font-medium mb-2">Top 主机</h4>
                  <div className="space-y-1">
                    {httpAnalysis.top_hosts?.slice(0, 10).map((h: { host: string; count: number }) => (
                      <div key={h.host} className="flex justify-between text-sm">
                        <span className="font-mono truncate">{h.host}</span>
                        <span className="text-muted-foreground">{h.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-2">请求方法</h4>
                  <div className="flex gap-2 flex-wrap">
                    {Object.entries(httpAnalysis.methods || {}).map(([method, count]) => (
                      <span key={method} className="px-2 py-1 bg-accent rounded text-sm">
                        {method}: {count as number}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-muted-foreground">暂无 HTTP 数据</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
