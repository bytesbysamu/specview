# 🛠️ Task 3: Agent Execution Pipeline

**Purpose**: Connect spec blocks to sandboxed containers via WebSocket, enabling users to execute specifications and stream Claude Code output back to the editor in real-time.

**Effort**: 3 days

**Dependencies**: Task 1 (Container Infrastructure), Task 2 (Real-time Communication)

**Parallel With**: —

**Blocks**: Task 4 (File Sync), Task 5 (Editor Integration)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Spec block execution trigger from editor
- Claude Code process spawning with `--dangerously-skip-permissions`
- Stdout/stderr streaming back to client via WebSocket
- Generated file list parsing and display
- Timeout handling and graceful error recovery
- Execution state management (idle, running, completed, failed)

### What's NOT Included
- File content synchronization back to editor — Task 4
- Editor UI for triggering execution — Task 5
- Multi-agent orchestration — Future iteration
- Spec block dependency resolution — Future iteration

---

## Prerequisites

Before starting:
- Container infrastructure operational (Task 1)
- WebSocket server running with room-based routing (Task 2)
- Claude CLI installed in container images
- Understanding of Node.js child process spawning
- Familiarity with WebSocket message protocols

---

## Implementation Steps

### Step 1: Define Execution Protocol

**File**: `shared/protocols/execution.ts`

**Purpose**: Establish the message contract between editor and container for execution requests and responses.

The protocol defines message types for the full execution lifecycle. Keep message payloads minimal—send spec content, receive streamed output chunks and final results.

**Pattern**:
```typescript
// Execution request from editor to container
interface ExecutionRequest {
  type: 'execute';
  requestId: string;
  specBlockId: string;
  specContent: string;
  workingDir?: string;  // Relative to container workspace
}

// Streamed output from container to editor
interface ExecutionOutput {
  type: 'output';
  requestId: string;
  stream: 'stdout' | 'stderr';
  chunk: string;
  timestamp: number;
}

// Execution completion
interface ExecutionComplete {
  type: 'complete';
  requestId: string;
  exitCode: number;
  filesCreated: string[];
  filesModified: string[];
  durationMs: number;
}

// Execution error (timeout, spawn failure, etc.)
interface ExecutionError {
  type: 'error';
  requestId: string;
  errorCode: 'TIMEOUT' | 'SPAWN_FAILED' | 'CONTAINER_UNAVAILABLE';
  message: string;
}
```

### Step 2: Implement Agent Spawner

**File**: `container-agent/src/spawner.ts`

**Purpose**: Spawn Claude Code processes inside the container with proper flags and environment.

This runs inside the container. It receives spec content, writes it to a temp file, spawns Claude Code pointing at that file, and emits events for stdout/stderr chunks.

**Pattern**:
```typescript
import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';

interface SpawnOptions {
  specContent: string;
  workingDir: string;
  timeoutMs: number;
}

class AgentSpawner extends EventEmitter {
  private process: ChildProcess | null = null;
  private timeoutHandle: NodeJS.Timeout | null = null;

  async spawn(options: SpawnOptions): Promise<void> {
    const { specContent, workingDir, timeoutMs } = options;
    
    // Write spec to temp file for Claude to read
    const specPath = path.join(workingDir, '.spec-input.md');
    await fs.writeFile(specPath, specContent, 'utf-8');

    // Spawn Claude Code with dangerous permissions flag
    this.process = spawn('claude', [
      '-p', specContent,  // Pass spec as prompt
      '--dangerously-skip-permissions',
      '--output-format', 'stream-json'
    ], {
      cwd: workingDir,
      env: { ...process.env, CLAUDE_CODE_NO_TELEMETRY: '1' }
    });

    this.setupStreams();
    this.setupTimeout(timeoutMs);
  }

  private setupStreams(): void {
    this.process.stdout.on('data', (chunk) => {
      this.emit('stdout', chunk.toString());
    });

    this.process.stderr.on('data', (chunk) => {
      this.emit('stderr', chunk.toString());
    });

    this.process.on('close', (code) => {
      this.clearTimeout();
      this.emit('close', code);
    });

    this.process.on('error', (err) => {
      this.clearTimeout();
      this.emit('error', err);
    });
  }

  private setupTimeout(ms: number): void {
    this.timeoutHandle = setTimeout(() => {
      if (this.process) {
        this.process.kill('SIGTERM');
        // Give 5s grace period, then SIGKILL
        setTimeout(() => this.process?.kill('SIGKILL'), 5000);
        this.emit('timeout');
      }
    }, ms);
  }

  private clearTimeout(): void {
    if (this.timeoutHandle) {
      clearTimeout(this.timeoutHandle);
      this.timeoutHandle = null;
    }
  }

  abort(): void {
    this.process?.kill('SIGTERM');
    this.clearTimeout();
  }
}
```

### Step 3: Build Execution Controller

**File**: `container-agent/src/execution-controller.ts`

**Purpose**: Coordinate between WebSocket messages and the agent spawner, managing execution state and output buffering.

The controller tracks active executions, prevents duplicate runs on the same spec block, and assembles completion results including file change detection.

**Pattern**:
```typescript
import { AgentSpawner } from './spawner';
import { WebSocketConnection } from './websocket';
import { FileWatcher } from './file-watcher';

interface ActiveExecution {
  requestId: string;
  specBlockId: string;
  spawner: AgentSpawner;
  startTime: number;
  filesAtStart: Set<string>;
}

class ExecutionController {
  private active: Map<string, ActiveExecution> = new Map();
  private ws: WebSocketConnection;
  private workspaceDir: string;
  private defaultTimeoutMs = 5 * 60 * 1000; // 5 minutes

  async handleExecuteRequest(request: ExecutionRequest): Promise<void> {
    // Prevent duplicate execution on same spec block
    if (this.isSpecBlockRunning(request.specBlockId)) {
      this.ws.send({
        type: 'error',
        requestId: request.requestId,
        errorCode: 'ALREADY_RUNNING',
        message: `Spec block ${request.specBlockId} is already executing`
      });
      return;
    }

    const workingDir = path.join(this.workspaceDir, request.workingDir || '');
    const filesAtStart = await this.listFiles(workingDir);
    
    const spawner = new AgentSpawner();
    const execution: ActiveExecution = {
      requestId: request.requestId,
      specBlockId: request.specBlockId,
      spawner,
      startTime: Date.now(),
      filesAtStart
    };

    this.active.set(request.requestId, execution);
    this.bindSpawnerEvents(execution);

    try {
      await spawner.spawn({
        specContent: request.specContent,
        workingDir,
        timeoutMs: this.defaultTimeoutMs
      });
    } catch (err) {
      this.handleSpawnError(execution, err);
    }
  }

  private bindSpawnerEvents(execution: ActiveExecution): void {
    const { spawner, requestId } = execution;

    spawner.on('stdout', (chunk) => {
      this.ws.send({
        type: 'output',
        requestId,
        stream: 'stdout',
        chunk,
        timestamp: Date.now()
      });
    });

    spawner.on('stderr', (chunk) => {
      this.ws.send({
        type: 'output',
        requestId,
        stream: 'stderr',
        chunk,
        timestamp: Date.now()
      });
    });

    spawner.on('close', async (exitCode) => {
      const fileChanges = await this.detectFileChanges(execution);
      this.ws.send({
        type: 'complete',
        requestId,
        exitCode,
        filesCreated: fileChanges.created,
        filesModified: fileChanges.modified,
        durationMs: Date.now() - execution.startTime
      });
      this.active.delete(requestId);
    });

    spawner.on('timeout', () => {
      this.ws.send({
        type: 'error',
        requestId,
        errorCode: 'TIMEOUT',
        message: 'Execution timed out after 5 minutes'
      });
      this.active.delete(requestId);
    });
  }

  private async detectFileChanges(execution: ActiveExecution) {
    const currentFiles = await this.listFiles(this.workspaceDir);
    const created = [...currentFiles].filter(f => !execution.filesAtStart.has(f));
    const modified = await this.findModifiedFiles(execution.filesAtStart, currentFiles);
    return { created, modified };
  }
}
```

### Step 4: Parse Generated File List

**File**: `container-agent/src/output-parser.ts`

**Purpose**: Extract structured information from Claude Code's output stream, including file operations and tool calls.

Claude Code with `--output-format stream-json` emits JSON lines. Parse these to extract file write operations and build the generated file list.

**Pattern**:
```typescript
interface ParsedOutput {
  type: 'text' | 'tool_use' | 'tool_result';
  content?: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
}

class OutputParser {
  private buffer = '';
  private filesWritten: string[] = [];

  parse(chunk: string): ParsedOutput[] {
    this.buffer += chunk;
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop() || ''; // Keep incomplete line in buffer

    return lines
      .filter(line => line.trim())
      .map(line => this.parseLine(line))
      .filter(Boolean);
  }

  private parseLine(line: string): ParsedOutput | null {
    try {
      const json = JSON.parse(line);
      
      // Track file writes from tool calls
      if (json.type === 'tool_use' && json.name === 'Write') {
        this.filesWritten.push(json.input.file_path);
      }
      
      return {
        type: json.type,
        content: json.content,
        toolName: json.name,
        toolInput: json.input
      };
    } catch {
      // Non-JSON output, treat as plain text
      return { type: 'text', content: line };
    }
  }

  getFilesWritten(): string[] {
    return [...this.filesWritten];
  }
}
```

### Step 5: Implement Client-Side Execution Manager

**File**: `src/app/services/execution.service.ts`

**Purpose**: Manage execution requests from the Angular editor, track execution state, and handle incoming output streams.

This service lives in the Angular frontend. It sends execution requests over WebSocket and updates UI state as output streams back.

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { WebSocketService } from './websocket.service';

interface ExecutionState {
  status: 'idle' | 'running' | 'completed' | 'failed';
  output: string;
  filesCreated: string[];
  filesModified: string[];
  error?: string;
}

@Injectable({ providedIn: 'root' })
export class ExecutionService {
  private executions = new Map<string, BehaviorSubject<ExecutionState>>();
  
  constructor(private ws: WebSocketService) {
    this.ws.messages$.subscribe(msg => this.handleMessage(msg));
  }

  execute(specBlockId: string, specContent: string): BehaviorSubject<ExecutionState> {
    const requestId = crypto.randomUUID();
    const state$ = new BehaviorSubject<ExecutionState>({
      status: 'running',
      output: '',
      filesCreated: [],
      filesModified: []
    });

    this.executions.set(requestId, state$);

    this.ws.send({
      type: 'execute',
      requestId,
      specBlockId,
      specContent
    });

    return state$;
  }

  private handleMessage(msg: any): void {
    const state$ = this.executions.get(msg.requestId);
    if (!state$) return;

    const current = state$.value;

    switch (msg.type) {
      case 'output':
        state$.next({
          ...current,
          output: current.output + msg.chunk
        });
        break;

      case 'complete':
        state$.next({
          ...current,
          status: msg.exitCode === 0 ? 'completed' : 'failed',
          filesCreated: msg.filesCreated,
          filesModified: msg.filesModified
        });
        break;

      case 'error':
        state$.next({
          ...current,
          status: 'failed',
          error: msg.message
        });
        break;
    }
  }

  abort(requestId: string): void {
    this.ws.send({ type: 'abort', requestId });
  }
}
```

### Step 6: Add Error Recovery

**File**: `container-agent/src/error-handler.ts`

**Purpose**: Handle edge cases like container restarts, WebSocket disconnects during execution, and Claude Code crashes.

Graceful error handling ensures users get meaningful feedback rather than silent failures.

**Pattern**:
```typescript
class ExecutionErrorHandler {
  handleSpawnError(execution: ActiveExecution, error: Error): void {
    const errorCode = this.classifyError(error);
    
    this.ws.send({
      type: 'error',
      requestId: execution.requestId,
      errorCode,
      message: this.getUserMessage(errorCode, error)
    });

    this.cleanup(execution);
  }

  private classifyError(error: Error): string {
    if (error.message.includes('ENOENT')) {
      return 'CLAUDE_NOT_FOUND';
    }
    if (error.message.includes('ENOMEM')) {
      return 'OUT_OF_MEMORY';
    }
    return 'SPAWN_FAILED';
  }

  private getUserMessage(code: string, error: Error): string {
    const messages: Record<string, string> = {
      CLAUDE_NOT_FOUND: 'Claude CLI not found in container. Contact support.',
      OUT_OF_MEMORY: 'Container ran out of memory. Try a smaller spec.',
      SPAWN_FAILED: `Failed to start execution: ${error.message}`
    };
    return messages[code] || error.message;
  }

  handleDisconnect(activeExecutions: Map<string, ActiveExecution>): void {
    // Abort all running executions on WebSocket disconnect
    for (const execution of activeExecutions.values()) {
      execution.spawner.abort();
    }
    activeExecutions.clear();
  }
}
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Start the container with agent
docker run -d --name test-container spec-doc-container

# 2. Connect WebSocket client (use wscat or similar)
wscat -c ws://localhost:3100/ws/container/test-container

# 3. Send execution request
{"type":"execute","requestId":"test-1","specBlockId":"block-1","specContent":"Create a file called hello.txt with 'Hello World'"}

# 4. Observe streamed output
# Should see stdout chunks as Claude works
# Should see completion message with filesCreated: ["hello.txt"]

# 5. Verify file was created
docker exec test-container cat /workspace/hello.txt
```

**Expected Result**: 
- WebSocket receives `output` messages with Claude's stdout/stderr
- Final `complete` message shows `exitCode: 0` and `filesCreated` array
- File exists in container at expected path
- Timeout triggers `error` message after 5 minutes if execution hangs

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 3 done
2. Proceed to Task 4 (File Synchronization)
3. Integration test: combine Tasks 1-3 for end-to-end spec execution

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for execution isolation
- [Epic](./epic.md) – Task scope and acceptance criteria
- [Timeline](./timeline.md) – Status tracking