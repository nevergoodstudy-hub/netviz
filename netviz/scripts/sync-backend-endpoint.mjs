import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const rootDir = path.resolve(__dirname, '..')

const backendConfigPath = path.join(rootDir, 'config', 'backend-endpoint.json')
const tauriConfigPath = path.join(rootDir, 'src-tauri', 'tauri.conf.json')

const buildOrigin = ({ protocol, host, port }) => `${protocol}://${host}:${port}`

const buildWsOrigin = ({ protocol, host, port }) => {
  const wsProtocol = protocol === 'https' ? 'wss' : 'ws'
  return `${wsProtocol}://${host}:${port}`
}

const parseCsp = (csp) => {
  const directives = new Map()

  for (const clause of csp.split(';').map((part) => part.trim()).filter(Boolean)) {
    const [name, ...values] = clause.split(/\s+/)
    directives.set(name, values)
  }

  return directives
}

const stringifyCsp = (directives) =>
  `${Array.from(directives.entries())
    .map(([name, values]) => [name, ...values].join(' ').trim())
    .join('; ')};`

const backendConfig = JSON.parse(await fs.readFile(backendConfigPath, 'utf8'))
const tauriConfig = JSON.parse(await fs.readFile(tauriConfigPath, 'utf8'))

const desktopBackend = backendConfig.desktop
const backendOrigin = buildOrigin(desktopBackend)
const backendWsOrigin = buildWsOrigin(desktopBackend)

tauriConfig.app ??= {}
tauriConfig.app.security ??= {}

const directives = parseCsp(
  tauriConfig.app.security.csp ??
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https: blob:; connect-src 'self'; font-src 'self' data:;"
)

directives.set('connect-src', [
  "'self'",
  backendOrigin,
  backendWsOrigin,
])

tauriConfig.app.security.csp = stringifyCsp(directives)

await fs.writeFile(tauriConfigPath, `${JSON.stringify(tauriConfig, null, 2)}\n`, 'utf8')

console.log(
  `[sync-backend-endpoint] synchronized desktop backend origins: ${backendOrigin} / ${backendWsOrigin}`
)
