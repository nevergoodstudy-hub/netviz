import backendEndpointConfig from '../../config/backend-endpoint.json'

type DesktopBackendConfig = {
  protocol: 'http' | 'https'
  host: string
  port: number
  apiBasePath: string
  websocketPath: string
}

const desktopBackend = backendEndpointConfig.desktop as DesktopBackendConfig

const normalizePath = (value: string): string => {
  if (!value || value === '/') {
    return '/'
  }

  return value.startsWith('/') ? value : `/${value}`
}

const joinOriginAndPath = (origin: string, path: string): string => {
  const normalizedPath = normalizePath(path)
  return normalizedPath === '/' ? origin : `${origin}${normalizedPath}`
}

export const desktopBackendOrigin = `${desktopBackend.protocol}://${desktopBackend.host}:${desktopBackend.port}`

export const desktopBackendWsOrigin = `${desktopBackend.protocol === 'https' ? 'wss' : 'ws'}://${desktopBackend.host}:${desktopBackend.port}`

export const desktopBackendApiBaseUrl = joinOriginAndPath(
  desktopBackendOrigin,
  desktopBackend.apiBasePath
)

export const desktopBackendWsUrl = joinOriginAndPath(
  desktopBackendWsOrigin,
  desktopBackend.websocketPath
)
