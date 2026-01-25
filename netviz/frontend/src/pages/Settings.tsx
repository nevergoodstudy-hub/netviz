import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, X, Loader2, Eye, EyeOff } from 'lucide-react'
import { settingsApi } from '@/services/api'
import { toast } from '@/components/ui/Toaster'

export default function Settings() {
  const queryClient = useQueryClient()

  const { data: providers } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: () => settingsApi.getAIProviders().then((r) => r.data),
  })

  const { data: systemInfo } = useQuery({
    queryKey: ['system-info'],
    queryFn: () => settingsApi.getSystemInfo().then((r) => r.data),
  })

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">设置</h1>

      {/* AI 提供商配置 */}
      <div className="bg-card border rounded-lg">
        <div className="p-4 border-b">
          <h2 className="font-semibold">AI 提供商配置</h2>
          <p className="text-sm text-muted-foreground mt-1">
            配置 AI 服务的 API 密钥和模型
          </p>
        </div>
        <div className="divide-y">
          {providers?.map((provider: { provider: string; configured: boolean; model: string; status: string }) => (
            <ProviderConfig
              key={provider.provider}
              provider={provider.provider}
              configured={provider.configured}
              model={provider.model}
              status={provider.status}
            />
          ))}
        </div>
      </div>

      {/* 系统信息 */}
      <div className="bg-card border rounded-lg">
        <div className="p-4 border-b">
          <h2 className="font-semibold">系统信息</h2>
        </div>
        <div className="p-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">应用名称</span>
            <span>{systemInfo?.app_name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Python 版本</span>
            <span className="font-mono">{systemInfo?.python_version?.split(' ')[0]}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">系统平台</span>
            <span className="font-mono">{systemInfo?.platform}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">调试模式</span>
            <span>{systemInfo?.debug_mode ? '是' : '否'}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function ProviderConfig({
  provider,
  configured,
  model,
  status,
}: {
  provider: string
  configured: boolean
  model: string
  status: string
}) {
  const queryClient = useQueryClient()
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [newModel, setNewModel] = useState(model)
  const [baseUrl, setBaseUrl] = useState('')
  const [editing, setEditing] = useState(false)

  const configMutation = useMutation({
    mutationFn: () =>
      settingsApi.configureAIProvider({
        provider,
        api_key: apiKey || undefined,
        model: newModel !== model ? newModel : undefined,
        base_url: baseUrl || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] })
      toast({ title: '配置已保存', type: 'success' })
      setEditing(false)
      setApiKey('')
    },
    onError: () => {
      toast({ title: '保存失败', type: 'error' })
    },
  })

  const testMutation = useMutation({
    mutationFn: () => settingsApi.testAIProvider(provider),
    onSuccess: (res) => {
      if (res.data.status === 'success') {
        toast({ title: '连接成功', description: res.data.message, type: 'success' })
      } else {
        toast({ title: '连接失败', description: res.data.message, type: 'error' })
      }
    },
    onError: () => {
      toast({ title: '测试失败', type: 'error' })
    },
  })

  const providerNames: Record<string, string> = {
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    ollama: 'Ollama (本地)',
    deepseek: 'DeepSeek',
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="font-medium">{providerNames[provider] || provider}</span>
          <span
            className={`px-2 py-0.5 text-xs rounded-full ${
              configured
                ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
            }`}
          >
            {status === 'local' ? '本地服务' : configured ? '已配置' : '未配置'}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending || (!configured && provider !== 'ollama')}
            className="px-3 py-1 text-sm border rounded hover:bg-accent disabled:opacity-50"
          >
            {testMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              '测试连接'
            )}
          </button>
          <button
            onClick={() => setEditing(!editing)}
            className="px-3 py-1 text-sm border rounded hover:bg-accent"
          >
            {editing ? '取消' : '编辑'}
          </button>
        </div>
      </div>

      {editing && (
        <div className="space-y-3 mt-4">
          {provider !== 'ollama' && (
            <div>
              <label className="text-sm text-muted-foreground">API Key</label>
              <div className="flex gap-2 mt-1">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="输入 API Key"
                  className="flex-1 px-3 py-2 border rounded-lg bg-background"
                />
                <button
                  onClick={() => setShowKey(!showKey)}
                  className="p-2 border rounded-lg hover:bg-accent"
                >
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
          )}

          {provider === 'ollama' && (
            <div>
              <label className="text-sm text-muted-foreground">Base URL</label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="http://localhost:11434"
                className="w-full px-3 py-2 border rounded-lg bg-background mt-1"
              />
            </div>
          )}

          <div>
            <label className="text-sm text-muted-foreground">模型</label>
            <input
              type="text"
              value={newModel}
              onChange={(e) => setNewModel(e.target.value)}
              placeholder="模型名称"
              className="w-full px-3 py-2 border rounded-lg bg-background mt-1"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => configMutation.mutate()}
              disabled={configMutation.isPending}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 inline-flex items-center gap-2"
            >
              {configMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Check className="h-4 w-4" />
              )}
              保存
            </button>
            <button
              onClick={() => {
                setEditing(false)
                setApiKey('')
                setNewModel(model)
              }}
              className="px-4 py-2 border rounded-lg hover:bg-accent inline-flex items-center gap-2"
            >
              <X className="h-4 w-4" />
              取消
            </button>
          </div>
        </div>
      )}

      {!editing && (
        <div className="text-sm text-muted-foreground">
          当前模型: <span className="font-mono">{model}</span>
        </div>
      )}
    </div>
  )
}
