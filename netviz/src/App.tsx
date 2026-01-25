import { Suspense, lazy } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/Toaster'
import Layout from '@/components/Layout'

// 懒加载页面组件
const Dashboard = lazy(() => import('@/pages/Dashboard'))
const PcapList = lazy(() => import('@/pages/PcapList'))
const PcapDetail = lazy(() => import('@/pages/PcapDetail'))
const Analysis = lazy(() => import('@/pages/Analysis'))
const Capture = lazy(() => import('@/pages/Capture'))
const AIChat = lazy(() => import('@/pages/AIChat'))
const Settings = lazy(() => import('@/pages/Settings'))

// 加载占位组件
function PageLoading() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
    </div>
  )
}

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={
            <Suspense fallback={<PageLoading />}>
              <Dashboard />
            </Suspense>
          } />
          <Route path="pcap" element={
            <Suspense fallback={<PageLoading />}>
              <PcapList />
            </Suspense>
          } />
          <Route path="pcap/:id" element={
            <Suspense fallback={<PageLoading />}>
              <PcapDetail />
            </Suspense>
          } />
          <Route path="analysis" element={
            <Suspense fallback={<PageLoading />}>
              <Analysis />
            </Suspense>
          } />
          <Route path="capture" element={
            <Suspense fallback={<PageLoading />}>
              <Capture />
            </Suspense>
          } />
          <Route path="ai" element={
            <Suspense fallback={<PageLoading />}>
              <AIChat />
            </Suspense>
          } />
          <Route path="settings" element={
            <Suspense fallback={<PageLoading />}>
              <Settings />
            </Suspense>
          } />
        </Route>
      </Routes>
      <Toaster />
    </>
  )
}

export default App
