import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import * as Tabs from '@radix-ui/react-tabs'
import { ArrowLeft, Loader2 } from 'lucide-react'
import ReactECharts from 'echarts-for-react'
import { pcapApi, analysisApi } from '@/services/api'
import { formatBytes, formatNumber } from '@/lib/utils'
import { cn } from '@/lib/utils'

export default function PcapDetail() {
  const { id } = useParams<{ id: string }>()
  const pcapId = parseInt(id || '0')

  const { data: pcap, isLoading } = useQuery({
    queryKey: ['pcap', pcapId],
    queryFn: () => pcapApi.get(pcapId).then((r) => r.data),
    enabled: !!pcapId,
  })

  const { data: stats } = useQuery({
    queryKey: ['pcap-stats', pcapId],
    queryFn: () => pcapApi.getStats(pcapId).then((r) => r.data),
    enabled: !!pcapId,
  })

  const { data: protocolDist } = useQuery({
    queryKey: ['protocol-dist', pcapId],
    queryFn: () => analysisApi.getProtocolDistribution(pcapId).then((r) => r.data),
    enabled: !!pcapId,
  })

  const { data: timeSeries } = useQuery({
    queryKey: ['time-series', pcapId],
    queryFn: () => analysisApi.getTimeSeries(pcapId).then((r) => r.data),
    enabled: !!pcapId,
  })

  const { data: topTalkers } = useQuery({
    queryKey: ['top-talkers', pcapId],
    queryFn: () => analysisApi.getTopTalkers(pcapId).then((r) => r.data),
    enabled: !!pcapId,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!pcap) {
    return (
      <div className="p-6 text-center">
        <p className="text-muted-foreground">文件不存在</p>
        <Link to="/pcap" className="text-primary hover:underline mt-2 inline-block">
          返回列表
        </Link>
      </div>
    )
  }

  const protocolChartOption = {
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        data:
          protocolDist?.map((p: { protocol: string; count: number }) => ({
            name: p.protocol,
            value: p.count,
          })) || [],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
      },
    ],
  }

  const timeSeriesOption = {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: timeSeries?.map((t: { timestamp: string }) => new Date(t.timestamp).toLocaleTimeString()) || [],
    },
    yAxis: [
      { type: 'value', name: '数据包' },
      { type: 'value', name: '字节', position: 'right' },
    ],
    series: [
      {
        name: '数据包',
        type: 'line',
        data: timeSeries?.map((t: { packets: number }) => t.packets) || [],
        smooth: true,
      },
      {
        name: '字节',
        type: 'line',
        yAxisIndex: 1,
        data: timeSeries?.map((t: { bytes: number }) => t.bytes) || [],
        smooth: true,
      },
    ],
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/pcap" className="p-2 hover:bg-accent rounded-lg">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">{pcap.filename}</h1>
          <p className="text-sm text-muted-foreground">
            {formatBytes(pcap.file_size)} · {formatNumber(pcap.packet_count)} 个数据包
          </p>
        </div>
      </div>

      {/* 统计信息 */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="总数据包" value={formatNumber(stats.total_packets)} />
          <StatCard label="总字节数" value={formatBytes(stats.total_bytes)} />
          <StatCard label="唯一 IP" value={formatNumber(stats.unique_ips)} />
          <StatCard label="连接数" value={formatNumber(stats.total_connections)} />
        </div>
      )}

      {/* 标签页 */}
      <Tabs.Root defaultValue="overview" className="bg-card border rounded-lg">
        <Tabs.List className="flex border-b">
          {['overview', 'packets', 'connections', 'topology'].map((tab) => (
            <Tabs.Trigger
              key={tab}
              value={tab}
              className={cn(
                'px-4 py-3 text-sm font-medium transition-colors',
                'data-[state=active]:border-b-2 data-[state=active]:border-primary',
                'data-[state=active]:text-primary',
                'data-[state=inactive]:text-muted-foreground hover:text-foreground'
              )}
            >
              {tab === 'overview' && '概览'}
              {tab === 'packets' && '数据包'}
              {tab === 'connections' && '连接'}
              {tab === 'topology' && '拓扑'}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        <Tabs.Content value="overview" className="p-6 space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold mb-4">协议分布</h3>
              <ReactECharts option={protocolChartOption} style={{ height: 300 }} />
            </div>
            <div>
              <h3 className="font-semibold mb-4">流量时序</h3>
              <ReactECharts option={timeSeriesOption} style={{ height: 300 }} />
            </div>
          </div>

          {topTalkers && topTalkers.length > 0 && (
            <div>
              <h3 className="font-semibold mb-4">Top 通信者</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">IP 地址</th>
                      <th className="text-right p-2">数据包</th>
                      <th className="text-right p-2">字节</th>
                      <th className="text-right p-2">连接数</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topTalkers.map((talker: { ip: string; packets: number; bytes: number; connections: number }) => (
                      <tr key={talker.ip} className="border-b">
                        <td className="p-2 font-mono">{talker.ip}</td>
                        <td className="text-right p-2">{formatNumber(talker.packets)}</td>
                        <td className="text-right p-2">{formatBytes(talker.bytes)}</td>
                        <td className="text-right p-2">{formatNumber(talker.connections)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Tabs.Content>

        <Tabs.Content value="packets" className="p-6">
          <PacketList pcapId={pcapId} />
        </Tabs.Content>

        <Tabs.Content value="connections" className="p-6">
          <ConnectionList pcapId={pcapId} />
        </Tabs.Content>

        <Tabs.Content value="topology" className="p-6">
          <div className="text-center text-muted-foreground py-12">
            网络拓扑图（开发中）
          </div>
        </Tabs.Content>
      </Tabs.Root>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-card border rounded-lg p-4">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  )
}

function PacketList({ pcapId }: { pcapId: number }) {
  const { data: packets, isLoading } = useQuery({
    queryKey: ['packets', pcapId],
    queryFn: () => pcapApi.getPackets(pcapId, { limit: 100 }).then((r) => r.data),
  })

  if (isLoading) {
    return <div className="text-center py-8"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left p-2">#</th>
            <th className="text-left p-2">时间</th>
            <th className="text-left p-2">源地址</th>
            <th className="text-left p-2">目的地址</th>
            <th className="text-left p-2">协议</th>
            <th className="text-right p-2">长度</th>
          </tr>
        </thead>
        <tbody>
          {packets?.map((pkt: {
            id: number
            timestamp: string
            src_ip: string
            src_port: number
            dst_ip: string
            dst_port: number
            protocol: string
            length: number
          }) => (
            <tr key={pkt.id} className="border-b hover:bg-accent/50">
              <td className="p-2">{pkt.id}</td>
              <td className="p-2 font-mono text-xs">{new Date(pkt.timestamp).toLocaleTimeString()}</td>
              <td className="p-2 font-mono">{pkt.src_ip}:{pkt.src_port}</td>
              <td className="p-2 font-mono">{pkt.dst_ip}:{pkt.dst_port}</td>
              <td className="p-2">{pkt.protocol}</td>
              <td className="p-2 text-right">{pkt.length}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ConnectionList({ pcapId }: { pcapId: number }) {
  const { data: connections, isLoading } = useQuery({
    queryKey: ['connections', pcapId],
    queryFn: () => pcapApi.getConnections(pcapId).then((r) => r.data),
  })

  if (isLoading) {
    return <div className="text-center py-8"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left p-2">源地址</th>
            <th className="text-left p-2">目的地址</th>
            <th className="text-left p-2">协议</th>
            <th className="text-right p-2">数据包</th>
            <th className="text-right p-2">发送</th>
            <th className="text-right p-2">接收</th>
          </tr>
        </thead>
        <tbody>
          {connections?.map((conn: {
            id: number
            src_ip: string
            src_port: number
            dst_ip: string
            dst_port: number
            protocol: string
            packet_count: number
            bytes_sent: number
            bytes_received: number
          }) => (
            <tr key={conn.id} className="border-b hover:bg-accent/50">
              <td className="p-2 font-mono">{conn.src_ip}:{conn.src_port}</td>
              <td className="p-2 font-mono">{conn.dst_ip}:{conn.dst_port}</td>
              <td className="p-2">{conn.protocol}</td>
              <td className="p-2 text-right">{conn.packet_count}</td>
              <td className="p-2 text-right">{formatBytes(conn.bytes_sent)}</td>
              <td className="p-2 text-right">{formatBytes(conn.bytes_received)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
