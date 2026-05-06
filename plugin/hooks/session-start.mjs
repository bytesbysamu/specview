#!/usr/bin/env node
/**
 * session-start.mjs — chain-agent-plugin SessionStart hook
 *
 * Detects whether the current working directory is inside the specview repo
 * (api/ or web-ng/) and emits a context JSON block that tells Claude which
 * stack is active and which reference files to load.
 *
 * Fails silently — any error writes nothing to stdout so Claude Code is
 * unaffected by hook failures.
 */
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const KNOWN_STACKS = [
  { stack: 'backend',  marker: 'api/conftest.py' },
  { stack: 'frontend', marker: 'web-ng/angular.json' },
];

function findGitRoot(start) {
  let dir = resolve(start);
  while (dir !== dirname(dir)) {
    if (existsSync(resolve(dir, '.git'))) return dir;
    dir = dirname(dir);
  }
  return null;
}

function classifyStack(gitRoot) {
  if (!gitRoot) return 'unknown';
  for (const { stack, marker } of KNOWN_STACKS) {
    if (existsSync(resolve(gitRoot, marker))) return stack;
  }
  return 'unknown';
}

function detectCwd(cwd) {
  const norm = cwd.replace(/\\/g, '/');
  if (norm.includes('/api/')) return 'backend';
  if (norm.includes('/web-ng/')) return 'frontend';
  return 'root';
}

function buildContext(gitRoot, stack, cwdStack) {
  const references = [];
  if (stack === 'backend' || cwdStack === 'backend') {
    references.push('references/chain-conventions.md');
    references.push('references/flask-conventions.md');
  }
  if (stack === 'frontend' || cwdStack === 'frontend') {
    references.push('references/angular-conventions.md');
  }
  if (references.length === 0) {
    references.push('references/chain-conventions.md');
    references.push('references/flask-conventions.md');
    references.push('references/angular-conventions.md');
  }
  return { stack: cwdStack !== 'root' ? cwdStack : stack, gitRoot, references };
}

try {
  const cwd = process.cwd();
  const gitRoot = findGitRoot(cwd);
  const repoStack = classifyStack(gitRoot);
  const cwdStack = detectCwd(cwd);
  const ctx = buildContext(gitRoot, repoStack, cwdStack);
  process.stdout.write(JSON.stringify(ctx) + '\n');
} catch {
  // Silent fail — hook errors must never block the session
}
