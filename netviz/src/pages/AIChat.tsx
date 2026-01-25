import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Send, Loader2, Bot, User, Sparkles } from 'lucide-react'
import { pcapApi, aiApi } from '@/services/api'
import { toast } from '@/components/ui/Toaster'
import { cn } from '@/lib/utils'
import type { AIProvider } from '@/types'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function AIChat() {
  const [selectedPcap, setSelectedPcap] = useState<number | null>(null)
  const [provider, setProvider] = useState<AIProvider>('openai')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [conversationId, setConversationId] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { data: pcapList } = useQuery({
    queryKey: ['pcap-list'],
    queryFn: () => pcapApi.list().then((r) => r.data),
  })

  const chatMutation = useMutation({
    mutationFn: (message: string) =>
      aiApi.chat({
        pcap_id: selectedPcap!,
        message,
        conversation_id: conversationId || undefined,
        provider,
      }),
    onSuccess: (res) => {
      setMessages((prev) => [...prev, { role: 'assistant', content: res.data.message || res.data.response || '' }])
      if (res.data.conversation_id) {
        setConversationId(res.data.conversation_id)
      }
    },
    onError: () => {
      toast({ title: 'AI 响应失败', description: '请检查 API 配置', type: 'error' })
    },
  })

  const summaryMutation = useMutation({
    mutationFn: () => aiApi.getSummary(selectedPcap!, provider as AIProvider),
    onSuccess: (res) => {
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: '请为我生成此 PCAP 文件的分析摘要' },
        { role: 'assistant', content: res.data.summary },
      ])
    },
    onError: () => {
      toast({ title: '生成摘要失败', type: 'error' })
    },
  })

  const analyzeMutation = useMutation({
    mutationFn: (type: string) => aiApi.analyze(selectedPcap!, type, provider as AIProvider),
    onSuccess: (res) => {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.data.analysis },
      ])
    },
    onError: () => {
      toast({ title: '分析失败', type: 'error' })
    },
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim() || !selectedPcap) return

    const message = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: message }])
    chatMutation.mutate(message)
  }

  const isLoading = chatMutation.isPending || summaryMutation.isPending || analyzeMutation.isPending

  return (
    <div className="flex flex-col h-full">
      {/* 头部 */}
      <div className="p-4 border-b flex items-center justify-between">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          AI 分析助手
        </h1>
        <div className="flex items-center gap-4">
          <select
            value={selectedPcap || ''}
            onChange={(e) => {
              setSelectedPcap(e.target.value ? parseInt(e.target.value) : null)
              setMessages([])
              setConversationId(null)
            }}
            className="px-3 py-2 border rounded-lg bg-background"
          >
            <option value="">选择 PCAP 文件</option>
            {pcapList?.items?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.original_filename}
              </option>
            ))}
          </select>
            <select
            value={provider}
            onChange={(e) => setProvider(e.target.value as AIProvider)}
            className="px-3 py-2 border rounded-lg bg-background"
          >
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="deepseek">DeepSeek</option>
            <option value="ollama">Ollama</option>
          </select>
        </div>
      </div>

      {/* 消息区域 */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {!selectedPcap ? (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            请先选择一个 PCAP 文件
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full space-y-6">
            <Sparkles className="h-12 w-12 text-primary opacity-50" />
            <p className="text-muted-foreground">开始与 AI 分析助手对话</p>
            <div className="flex gap-2 flex-wrap justify-center">
              <button
                onClick={() => summaryMutation.mutate()}
                disabled={isLoading}
                className="px-4 py-2 bg-accent rounded-lg hover:bg-accent/80 text-sm"
              >
                生成分析摘要
              </button>
              <button
                onClick={() => {
                  setMessages((prev) => [...prev, { role: 'user', content: '分析安全威胁' }])
                  analyzeMutation.mutate('security')
                }}
                disabled={isLoading}
                className="px-4 py-2 bg-accent rounded-lg hover:bg-accent/80 text-sm"
              >
                安全威胁分析
              </button>
              <button
                onClick={() => {
                  setMessages((prev) => [...prev, { role: 'user', content: '分析网络性能' }])
                  analyzeMutation.mutate('performance')
                }}
                disabled={isLoading}
                className="px-4 py-2 bg-accent rounded-lg hover:bg-accent/80 text-sm"
              >
                性能分析
              </button>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div
                key={i}
                className={cn(
                  'flex gap-3 max-w-3xl',
                  msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''
                )}
              >
                <div
                  className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
                    msg.role === 'user' ? 'bg-primary' : 'bg-accent'
                  )}
                >
                  {msg.role === 'user' ? (
                    <User className="h-4 w-4 text-primary-foreground" />
                  ) : (
                    <Bot className="h-4 w-4" />
                  )}
                </div>
                <div
                  className={cn(
                    'p-4 rounded-lg',
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-accent'
                  )}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-3 max-w-3xl">
                <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="p-4 rounded-lg bg-accent">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* 输入区域 */}
      {selectedPcap && (
        <div className="p-4 border-t">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder="输入问题..."
              disabled={isLoading}
              className="flex-1 px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
