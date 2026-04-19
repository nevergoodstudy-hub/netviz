import { spawnSync } from 'node:child_process'
import { accessSync, constants as fsConstants } from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..')
const backendRoot = path.join(projectRoot, 'backend')
const scriptPath = path.join(projectRoot, 'scripts', 'build_backend_sidecar.py')
const forwardedArgs = process.argv.slice(2)

const candidatePythons =
  process.platform === 'win32'
    ? [
        { command: path.join(backendRoot, '.venv', 'Scripts', 'python.exe'), args: [] },
        { command: 'python', args: [] },
        { command: 'py', args: ['-3'] },
      ]
    : [
        { command: path.join(backendRoot, '.venv', 'bin', 'python'), args: [] },
        { command: 'python3', args: [] },
        { command: 'python', args: [] },
      ]

function canRunPython(candidate) {
  if (path.isAbsolute(candidate.command)) {
    try {
      accessSync(candidate.command, fsConstants.F_OK)
    } catch {
      return false
    }
  }

  const probe = spawnSync(candidate.command, [...candidate.args, '--version'], {
    stdio: 'ignore',
    cwd: projectRoot,
    shell: false,
  })

  return probe.status === 0
}

for (const candidate of candidatePythons) {
  if (!canRunPython(candidate)) {
    continue
  }

  const result = spawnSync(
    candidate.command,
    [...candidate.args, scriptPath, ...forwardedArgs],
    {
      stdio: 'inherit',
      cwd: projectRoot,
      shell: false,
    }
  )

  if (typeof result.status === 'number') {
    process.exit(result.status)
  }

  if (result.error) {
    console.error(result.error.message)
  }
}

console.error(
  'No usable Python interpreter was found for building the backend sidecar. ' +
    'Install the backend development environment first.'
)
process.exit(1)
