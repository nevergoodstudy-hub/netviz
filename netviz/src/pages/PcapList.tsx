import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { FileUp, FileSearch, Trash2, Upload, Loader2 } from 'lucide-react'
import { pcapApi } from '@/services/api'
import { formatBytes, formatNumber } from '@/lib/utils'
import { toast } from '@/components/ui/Toaster'

export default function PcapList() {
  const queryClient = useQueryClient()
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

  const { data: pcapList, isLoading } = useQuery({
    queryKey: ['pcap-list'],
    queryFn: () => pcapApi.list().then((r) => r.data),
  })

  const deleteMutation = useMutation({
    mutationFn: pcapApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pcap-list'] })
      toast({ title: '删除成功', type: 'success' })
    },
    onError: () => {
      toast({ title: '删除失败', type: 'error' })
    },
  })

  const handleUpload = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return

    const file = files[0]
    if (!file.name.endsWith('.pcap') && !file.name.endsWith('.pcapng')) {
      toast({ title: '请上传 .pcap 或 .pcapng 文件', type: 'error' })
      return
    }

    setUploading(true)
    setUploadProgress(0)

    try {
      await pcapApi.upload(file, setUploadProgress)
      queryClient.invalidateQueries({ queryKey: ['pcap-list'] })
      toast({ title: '上传成功', description: '文件正在解析中...', type: 'success' })
    } catch {
      toast({ title: '上传失败', type: 'error' })
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
  }, [queryClient])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      handleUpload(e.dataTransfer.files)
    },
    [handleUpload]
  )

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">PCAP 文件管理</h1>

      {/* 上传区域 */}
      <div
        className="border-2 border-dashed rounded-lg p-8 text-center transition-colors hover:border-primary"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        {uploading ? (
          <div className="space-y-4">
            <Loader2 className="h-12 w-12 mx-auto text-primary animate-spin" />
            <div className="text-lg font-medium">上传中... {uploadProgress}%</div>
            <div className="w-64 mx-auto h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        ) : (
          <label className="cursor-pointer space-y-4 block">
            <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
            <div className="text-lg font-medium">拖拽文件到此处或点击上传</div>
            <div className="text-sm text-muted-foreground">支持 .pcap 和 .pcapng 格式</div>
            <input
              type="file"
              accept=".pcap,.pcapng"
              className="hidden"
              onChange={(e) => handleUpload(e.target.files)}
            />
          </label>
        )}
      </div>

      {/* 文件列表 */}
      <div className="bg-card border rounded-lg">
        <div className="p-4 border-b">
          <h2 className="font-semibold">文件列表</h2>
        </div>
        {isLoading ? (
          <div className="p-8 text-center">
            <Loader2 className="h-8 w-8 mx-auto animate-spin text-muted-foreground" />
          </div>
        ) : pcapList?.items && pcapList.items.length > 0 ? (
          <div className="divide-y">
            {pcapList.items.map((pcap) => (
              <div
                key={pcap.id}
                className="flex items-center justify-between p-4 hover:bg-accent/50 transition-colors"
              >
                <Link to={`/pcap/${pcap.id}`} className="flex items-center gap-4 flex-1">
                  <FileSearch className="h-8 w-8 text-primary" />
                  <div>
                    <div className="font-medium">{pcap.filename}</div>
                    <div className="text-sm text-muted-foreground">
                      {formatBytes(pcap.file_size)} · {formatNumber(pcap.total_packets)} 个数据包
                    </div>
                  </div>
                </Link>
                <div className="flex items-center gap-4">
                  <span
                    className={`px-2 py-1 text-xs rounded-full ${
                      pcap.status === 'completed'
                        ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                        : pcap.status === 'parsing'
                        ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
                        : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                    }`}
                  >
                    {pcap.status === 'completed' ? '已完成' : pcap.status === 'parsing' ? '解析中' : '失败'}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {new Date(pcap.created_at).toLocaleDateString('zh-CN')}
                  </span>
                  <button
                    onClick={() => {
                      if (confirm('确定要删除此文件吗？')) {
                        deleteMutation.mutate(pcap.id)
                      }
                    }}
                    className="p-2 text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-muted-foreground">
            <FileUp className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>暂无 PCAP 文件</p>
          </div>
        )}
      </div>
    </div>
  )
}
