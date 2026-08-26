/** Run project Python commands with the local virtual environment when available. */

import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import process from 'node:process';

const isWindows = process.platform === 'win32';
const candidates = [
  process.env.PYTHON,
  isWindows ? '.venv\\Scripts\\python.exe' : '.venv/bin/python',
  isWindows ? 'py' : 'python3',
  'python',
].filter(Boolean);

const args = process.argv.slice(2);
if (args.length === 0) {
  console.error('Usage: bun scripts/run_python.mjs <python arguments>');
  process.exit(2);
}

for (const executable of candidates) {
  const isPath = executable.includes('/') || executable.includes('\\');
  if (isPath && !existsSync(executable)) continue;

  const commandArgs = isWindows && executable === 'py' ? ['-3', ...args] : args;
  const result = spawnSync(executable, commandArgs, {
    cwd: process.cwd(),
    env: process.env,
    stdio: 'inherit',
  });

  if (!result.error) process.exit(result.status ?? 1);
  if (result.error.code !== 'ENOENT') {
    console.error(`Failed to start ${executable}: ${result.error.message}`);
    process.exit(1);
  }
}

console.error(
  'Python was not found. Create .venv first: python3 -m venv .venv && source .venv/bin/activate'
);
process.exit(127);

