import { Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/Toaster'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import PcapList from '@/pages/PcapList'
import PcapDetail from '@/pages/PcapDetail'
import Analysis from '@/pages/Analysis'
import Capture from '@/pages/Capture'
import AIChat from '@/pages/AIChat'
import Settings from '@/pages/Settings'

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="pcap" element={<PcapList />} />
          <Route path="pcap/:id" element={<PcapDetail />} />
          <Route path="analysis" element={<Analysis />} />
          <Route path="capture" element={<Capture />} />
          <Route path="ai" element={<AIChat />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
      <Toaster />
    </>
  )
}

export default App
