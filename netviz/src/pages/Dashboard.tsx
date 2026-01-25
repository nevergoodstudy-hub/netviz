import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { FileUp, FileSearch, AlertTriangle, Activity } from 'lucide-react'
import { pcapApi, analysisApi } from '@/services/api'
import { formatBytes, formatNumber } from '@/lib/utils'

export default function Dashboard() {
  const { data: pcapList } = useQuery({
    queryKey: ['pcap-list'],
    queryFn: () => pcapApi.list().then((r) => r.data),
  })

  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => analysisApi.getAlerts().then((r) => r.data),
  })

  const pcapItems = pcapList?.items || []
  const stats = {
    totalFiles: pcapItems.length,
    totalPackets: pcapItems.reduce((sum, p) => sum + (p.total_packets || 0), 0),
    totalBytes: pcapItems.reduce((sum, p) => sum + (p.file_size || 0), 0),
    alertCount: alerts?.length || 0,
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">仪表盘</h1>
        <Link
          to="/pcap"
          className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90"
        >
          <FileUp className="h-4 w-4" />
          上传 PCAP
        </Link>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={FileSearch}
          label="PCAP 文件"
          value={formatNumber(stats.totalFiles)}
          color="text-blue-500"
        />
        <StatCard
          icon={Activity}
          label="总数据包"
          value={formatNumber(stats.totalPackets)}
          color="text-green-500"
        />
        <StatCard
          icon={FileUp}
          label="总数据量"
          value={formatBytes(stats.totalBytes)}
          color="text-purple-500"
        />
        <StatCard
          icon={AlertTriangle}
          label="告警数量"
          value={formatNumber(stats.alertCount)}
          color="text-red-500"
        />
      </div>

      {/* 最近文件 */}
      <div className="bg-card border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">最近上传的文件</h2>
        {pcapItems.length > 0 ? (
          <div className="space-y-2">
            {pcapItems.slice(0, 5).map((pcap) => (
              <Link
                key={pcap.id}
                to={`/pcap/${pcap.id}`}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-accent transition-colors"
              >
                <div className="flex items-center gap-3">
                  <FileSearch className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <div className="font-medium">{pcap.filename}</div>
                    <div className="text-sm text-muted-foreground">
                      {formatBytes(pcap.file_size)} · {formatNumber(pcap.total_packets)} 个数据包
                    </div>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground">
                  {new Date(pcap.created_at).toLocaleDateString('zh-CN')}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            暂无 PCAP 文件，请先上传
          </div>
        )}
      </div>

      {/* 最近告警 */}
      {alerts && alerts.length > 0 && (
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">最近告警</h2>
          <div className="space-y-2">
            {alerts.slice(0, 5).map((alert) => (
              <div
                key={alert.id}
                className="flex items-center justify-between p-3 rounded-lg bg-accent/50"
              >
                <div className="flex items-center gap-3">
                  <AlertTriangle
                    className={`h-5 w-5 ${
                      alert.severity === 'high'
                        ? 'text-red-500'
                        : alert.severity === 'medium'
                        ? 'text-yellow-500'
                        : 'text-blue-500'
                    }`}
                  />
                  <span>{alert.title}</span>
                </div>
                <span className="text-sm text-muted-foreground">
                  {new Date(alert.detected_at).toLocaleString('zh-CN')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType
  label: string
  value: string
  color: string
}) {
  return (
    <div className="bg-card border rounded-lg p-6">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg bg-accent ${color}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div>
          <div className="text-sm text-muted-foreground">{label}</div>
          <div className="text-2xl font-bold">{value}</div>
        </div>
      </div>
    </div>
  )
}
