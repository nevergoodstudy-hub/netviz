import fs from 'node:fs'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const backendEndpointConfig = JSON.parse(
  fs.readFileSync(new URL('./config/backend-endpoint.json', import.meta.url), 'utf8')
)

const desktopBackend = backendEndpointConfig.desktop as {
  protocol: 'http' | 'https'
  host: string
  port: number
}

const desktopBackendOrigin = `${desktopBackend.protocol}://${desktopBackend.host}:${desktopBackend.port}`
const desktopBackendWsOrigin = `${desktopBackend.protocol === 'https' ? 'wss' : 'ws'}://${desktopBackend.host}:${desktopBackend.port}`

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: desktopBackendOrigin,
        changeOrigin: true,
      },
      '/ws': {
        target: desktopBackendWsOrigin,
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/echarts') || id.includes('node_modules/zrender')) {
            return 'charts'
          }

          if (
            id.includes('node_modules/react') ||
            id.includes('node_modules/react-dom') ||
            id.includes('node_modules/react-router')
          ) {
            return 'react-vendor'
          }
        },
      },
    },
  },
})
