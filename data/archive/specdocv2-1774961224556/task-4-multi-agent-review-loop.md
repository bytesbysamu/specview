The context you provided mentions "Multi-agent review loop" with a coder agent, reviewer agent, and fixer agent, but this doesn't match the current project's Task 4 which is "Agent Integration" (connecting specs to Claude Code). 

Based on the context you provided in your prompt describing the multi-agent review loop, I'll generate the implementation guide for that task.

# 🛠️ Task 4: Multi-Agent Review Loop

**Purpose**: Automate code quality enforcement by spawning reviewer agents that validate implementation against specs, with automatic fix iterations.

**Effort**: 2 days

**Dependencies**: Task 1 (Agent Integration base) must be complete — needs working agent spawning infrastructure

**Parallel With**: —

**Blocks**: Task 7 (Doc Update Suggestions) — review output feeds spec update recommendations

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Reviewer agent spawning in isolated session after coder completion
- Spec-to-implementation comparison logic
- Pass/fail output with specific issue list
- Fixer agent that addresses only failed criteria
- 3-iteration cap with status surfacing

### What's NOT Included
- Parallel reviewer agents — sequential only for clarity
- Custom review criteria per project — uses standard rubric
- Human-in-the-loop between iterations — fully automated until cap

---

## Prerequisites

Before starting:
- Agent spawning infrastructure working (from Agent Integration task)
- Claude CLI configured and accessible
- Understanding of how specs are passed to agents

---

## Implementation Steps

### Step 1: Define Review Result Interface

**File**: `src/app/models/review-result.model.ts`

**Purpose**: Type the reviewer agent's output for consistent handling

```typescript
interface ReviewResult {
  pass: boolean;
  criteria: ReviewCriterion[];
  summary: string;
}

interface ReviewCriterion {
  name: string;
  pass: boolean;
  issue?: string;  // Only present if fail
  location?: string;  // File:line if applicable
}
```

### Step 2: Create Reviewer Agent Prompt Builder

**File**: `src/app/services/prompts/reviewer-prompt.service.ts`

**Purpose**: Build the prompt that instructs the reviewer agent what to check

The reviewer needs three inputs:
1. Original spec (what was requested)
2. Implementation output (what the coder produced)
3. Review rubric (how to evaluate)

**Pattern**:
```typescript
buildReviewerPrompt(spec: string, implementation: string): string {
  return `
You are a code reviewer. Compare this implementation against the spec.

## Original Spec
${spec}

## Implementation
${implementation}

## Review Criteria
1. All spec requirements addressed
2. No scope creep (only what was specified)
3. Patterns match architecture doc
4. No obvious bugs or security issues

Output JSON matching ReviewResult interface.
Pass = all criteria pass. Fail = any criterion fails.
For failures, be specific: what's wrong and where.
`;
}
```

### Step 3: Create Fixer Agent Prompt Builder

**File**: `src/app/services/prompts/fixer-prompt.service.ts`

**Purpose**: Build targeted fix instructions from review failures

The fixer should only address failed criteria, not rewrite everything.

**Pattern**:
```typescript
buildFixerPrompt(
  implementation: string, 
  failures: ReviewCriterion[]
): string {
  const failureList = failures
    .filter(c => !c.pass)
    .map(c => `- ${c.name}: ${c.issue} (${c.location || 'general'})`)
    .join('\n');

  return `
Fix ONLY these issues. Do not refactor or improve other code.

## Current Implementation
${implementation}

## Issues to Fix
${failureList}

Output the corrected implementation.
`;
}
```

### Step 4: Implement Review Loop Orchestrator

**File**: `src/app/services/review-loop.service.ts`

**Purpose**: Coordinate the coder → reviewer → fixer cycle with iteration cap

This is the core logic. Key behaviors:
- Fresh session for each agent (isolation)
- Max 3 iterations total
- Exit early on pass
- Accumulate history for debugging

**Pattern**:
```typescript
@Injectable({ providedIn: 'root' })
export class ReviewLoopService {
  private readonly MAX_ITERATIONS = 3;

  async executeWithReview(
    spec: string,
    initialImplementation: string
  ): Promise<ReviewLoopResult> {
    let implementation = initialImplementation;
    let iteration = 0;
    const history: IterationRecord[] = [];

    while (iteration < this.MAX_ITERATIONS) {
      iteration++;
      
      // Spawn reviewer in fresh session
      const review = await this.spawnReviewer(spec, implementation);
      
      history.push({ iteration, review, implementation });

      if (review.pass) {
        return { 
          success: true, 
          finalImplementation: implementation,
          iterations: iteration,
          history 
        };
      }

      // Spawn fixer for failed criteria only
      implementation = await this.spawnFixer(
        implementation, 
        review.criteria.filter(c => !c.pass)
      );
    }

    // Hit cap without passing
    return {
      success: false,
      finalImplementation: implementation,
      iterations: iteration,
      history,
      reason: 'Max iterations reached'
    };
  }
}
```

### Step 5: Implement Agent Spawning with Session Isolation

**File**: `src/app/services/agent-spawner.service.ts`

**Purpose**: Spawn Claude agents in isolated sessions

Each agent must be a fresh session to avoid context pollution from previous iterations.

**Pattern**:
```typescript
async spawnAgent(prompt: string): Promise<string> {
  // Use Claude CLI with --new-session flag (or equivalent)
  // This ensures reviewer doesn't inherit coder's context
  return this.http.post<{ output: string }>(
    '/api/ai/agent',
    { 
      prompt,
      newSession: true  // Critical: isolation
    }
  ).toPromise().then(r => r.output);
}
```

**Backend addition** (`server.js`):

```javascript
app.post('/api/ai/agent', async (req, res) => {
  const { prompt, newSession } = req.body;
  
  // Spawn Claude with fresh context
  const sessionFlag = newSession ? '--conversation /dev/null' : '';
  const result = await exec(
    `claude ${sessionFlag} -p "${escapePrompt(prompt)}"`
  );
  
  res.json({ output: result.stdout });
});
```

### Step 6: Parse Reviewer Output

**File**: `src/app/services/review-parser.service.ts`

**Purpose**: Extract structured ReviewResult from agent text output

Agents output text; we need structured data. Handle JSON extraction with fallback.

**Pattern**:
```typescript
parseReviewOutput(output: string): ReviewResult {
  // Try to extract JSON block
  const jsonMatch = output.match(/```json\n([\s\S]*?)\n```/);
  
  if (jsonMatch) {
    try {
      return JSON.parse(jsonMatch[1]);
    } catch (e) {
      // Fall through to heuristic parsing
    }
  }
  
  // Heuristic fallback: look for pass/fail keywords
  const pass = /all criteria pass|implementation correct/i.test(output);
  return {
    pass,
    criteria: [],
    summary: output.slice(0, 500)
  };
}
```

### Step 7: Surface Status to UI

**File**: `src/app/components/review-status/review-status.component.ts`

**Purpose**: Show user what's happening during review loop

Users need visibility into the automated process.

**Pattern**:
```typescript
@Component({
  selector: 'app-review-status',
  template: `
    <div class="review-status" *ngIf="status">
      <div class="iteration">Iteration {{ status.current }} / {{ status.max }}</div>
      <div class="phase">{{ status.phase }}</div>
      <div class="criteria" *ngIf="status.lastReview">
        <div *ngFor="let c of status.lastReview.criteria"
             [class.pass]="c.pass" [class.fail]="!c.pass">
          {{ c.name }}: {{ c.pass ? '✓' : c.issue }}
        </div>
      </div>
    </div>
  `
})
export class ReviewStatusComponent {
  @Input() status: ReviewLoopStatus;
}
```

### Step 8: Integrate with Implement Button

**File**: `src/app/components/operation-bar/operation-bar.component.ts`

**Purpose**: Wire review loop into existing implement flow

The "Implement" button should now trigger the full loop, not just the coder.

**Pattern**:
```typescript
async onImplementClick() {
  this.status = { phase: 'coding', current: 0, max: 3 };
  
  // First: run coder agent
  const initialImpl = await this.agentService.implement(this.spec);
  
  // Then: review loop
  this.status.phase = 'reviewing';
  const result = await this.reviewLoop.executeWithReview(
    this.spec,
    initialImpl
  );
  
  // Surface final status
  this.status.phase = result.success ? 'passed' : 'max-iterations';
  this.onImplementComplete.emit(result);
}
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Start the dev server
npm run dev

# 2. Open browser to http://localhost:4201

# 3. Create a spec with intentional ambiguity that will fail review
# Example: "Add login button" (missing: where? what happens on click?)

# 4. Click Implement

# 5. Watch the review status component cycle through iterations
```

**Expected Result**: 
- Status shows "Iteration 1/3", "Iteration 2/3", etc.
- Each iteration shows which criteria passed/failed
- Loop exits early if all pass, or at iteration 3 if not
- Final implementation shown with review history available

**Test Cases**:
1. Perfect spec → Pass on iteration 1
2. Ambiguous spec → Multiple iterations, may hit cap
3. Impossible spec → Hits cap with clear failure reasons

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark done
2. Proceed to Task 7 (Doc Update Suggestions) which uses review output

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for agent spawning
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking