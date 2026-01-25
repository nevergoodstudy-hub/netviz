import { Outlet, NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  FileSearch,
  BarChart3,
  MessageSquare,
  Settings,
  Network,
  Wifi,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: '仪表盘' },
  { to: '/pcap', icon: FileSearch, label: 'PCAP 文件' },
  { to: '/capture', icon: Wifi, label: '实时抓包' },
  { to: '/analysis', icon: BarChart3, label: '流量分析' },
  { to: '/ai', icon: MessageSquare, label: 'AI 分析' },
  { to: '/settings', icon: Settings, label: '设置' },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-background">
      {/* 侧边栏 */}
      <aside className="w-64 border-r bg-card">
        <div className="flex h-16 items-center gap-2 border-b px-6">
          <Network className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold">NetViz</span>
        </div>
        <nav className="p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
