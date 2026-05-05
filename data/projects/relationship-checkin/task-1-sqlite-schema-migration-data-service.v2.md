# Task 1: SQLite Schema + Migration + Data Service

**Purpose**: Define the persistence layer for Relationship Check-In and provide an adapter service for all check-in data operations. Create the SQLite tables, versioned migration, static model definitions (ten questions, four qualities, thresholds), a mock data module, and the service that every downstream task consumes.

**Effort**: 1 day

**Dependencies**: None

**Parallel With**: --

**Blocks**: Tasks 2 (Partner Selection), 3 (Rating Interface), 4 (Results), 5 (Trends), 6 (Expiry) -- every task depends on this service and schema.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context + Trade-offs

The Relationship Check-In feature needs three SQLite tables (`checkin_session`, `checkin_response`, `checkin_quality_score`), a data service adapter, and a static model file defining the ten questions, four quality mappings, and interpretation thresholds. All downstream tasks (partner selection, rating, results, trends, expiry) depend on this foundation being correct and tested before they start.

The Bubls app already has a working SQLite infrastructure: `SqliteService` at `src/app/shared/sqlite/sqlite.service.ts` wraps `@capacitor-community/sqlite` with platform detection (native vs. web no-ops), versioned migrations via `addUpgradeStatements()`, and typed `query()`/`execute()` methods. The `AppSettingsService` at `src/app/shared/sqlite/app-settings.service.ts` demonstrates the exact consumer pattern: define migrations as a `Migration[]` constant, register them before first query, and use the shared `'bubls'` database name. This task follows that pattern verbatim.

**Trade-offs considered**:

- **Separate database per feature** -- rejected; `AppSettingsService` already uses `DB_NAME = 'bubls'` and the Capacitor SQLite plugin manages version numbers per database. A second database means a second version counter and a second `ensureOpen()` call. One database with namespaced table names (`checkin_*`) is simpler and matches the existing pattern.
- **ORM wrapper over SQLite queries** -- rejected; PRINCIPLES.md mandates "Always ORM, Never Raw SQL" for server-side Neon Postgres, but the client-side SQLite service uses raw parameterized statements (see `AppSettingsService.set()` which does `INSERT OR REPLACE` via `execute()`). Following the established client-side pattern avoids inventing an ORM abstraction where none exists. Parameterized values prevent injection.
- **Compute quality scores on read (view/projection)** -- rejected; architecture specifies materialized `checkin_quality_score` rows written at submit time so trend queries are a single `SELECT` without joins and aggregation. Write cost is negligible (4 rows per partner per session). Read simplicity wins.
- **UUID vs. CUID vs. timestamp-based IDs** -- use `crypto.randomUUID()` for all primary keys. Available in all target runtimes (iOS WebKit, modern browsers). Matches no existing convention in the codebase (AppSettingsService uses text keys, not generated IDs), but UUID is the simplest zero-dependency option.
- **Mock mode via environment flag vs. injectable strategy** -- architecture specifies mock mode gated by `MOCK_CHECKIN` environment flag, matching the existing `environment.useMocks` pattern (see `src/environments/environment.ts` where `useMocks.picks`, `useMocks.photoshoot`, etc. are per-feature booleans). Add `checkin: true` to `useMocks` and read it in the service constructor.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                                       # Flag any unrelated M/?? entries
git diff HEAD -- src/app/shared/sqlite/ src/environments/
npm test -- --watch=false --browsers=ChromeHeadless              # Baseline FE suite; record pass count
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting. The `src/app/shared/sqlite/` directory and `src/environments/` files must be clean at HEAD.

**Baseline recorded**: write the pass count here after running (format: `N/N passing`). This is the `N` referenced in section 7.

**Verify environment structure**: confirm `src/environments/environment.ts` exports a `useMocks` object with per-feature booleans. The new `checkin` flag will be added to this object.

---

## 3. Files (Create / Modify / Leave Alone)

### To Create (new)

- `src/app/pages/checkin/checkin.model.ts` -- Ten questions (text + quality mapping), four quality definitions (key, display name, constituent question indices), score thresholds, and TypeScript interfaces for `CheckinSession`, `CheckinResponse`, `CheckinQualityScore`.
- `src/app/pages/checkin/checkin.mock.ts` -- Three complete mock sessions with divergent scores for development and testing on web platform.
- `src/app/pages/checkin/checkin.service.ts` -- Adapter between UI signals and SQLite. Exposes `createSession()`, `submitResponses()`, `getActiveSession()`, `getSessionResults()`, `getQualityTrends()`, `expireStale()`. Internally calls `SqliteService` for persistence. Mock mode returns static fixture data when `environment.useMocks.checkin` is true.
- `src/app/pages/checkin/checkin.service.spec.ts` -- Unit tests with mock `SqliteService` (spy pattern from `app-settings.service.spec.ts`).

### To Modify (cite codebase context)

- `src/environments/environment.ts` -- Add `checkin: true` to the `useMocks` object (mock mode for development).
- `src/environments/environment.prod.ts` -- Add `checkin: true` to the `useMocks` object (mock mode until SQLite is wired on device).
- `src/environments/environment.lan.ts` -- Add `checkin: true` to the `useMocks` object (consistent across environments).

### To Leave Alone

- `src/app/shared/sqlite/sqlite.service.ts` -- No changes. Consumed as-is via `inject()`.
- `src/app/shared/sqlite/sqlite.model.ts` -- No changes. `Migration`, `QueryOptions`, `RunOptions`, `QueryResult` types are sufficient.
- `src/app/shared/sqlite/sqlite.mock.ts` -- Not used directly. The checkin service has its own mock strategy.
- `src/app/shared/sqlite/app-settings.service.ts` -- Reference pattern only. Do not modify.
- `src/app/shared/sqlite/index.ts` -- No new exports needed; checkin service imports `SqliteService` directly.
- `src/app/app.routes.ts` -- Route registration belongs to Task 2, not this task.
- `src/app/shell/` -- Shell changes belong to Task 2.
- `server/` -- No backend changes. This feature is local-only.

---

## 4. Implementation Steps

### Step 1: Read existing SQLite infrastructure

**Action**: Inspect the files you are about to depend on. Confirm `SqliteService` exposes `addUpgradeStatements()`, `query()`, `execute()`, and that `AppSettingsService` uses `DB_NAME = 'bubls'` with version-based migrations. Confirm the `Migration` interface shape: `{ version: number; statements: string[] }`.

**File**: `src/app/shared/sqlite/sqlite.service.ts`, `src/app/shared/sqlite/app-settings.service.ts`, `src/app/shared/sqlite/sqlite.model.ts`

**Pattern**:
```bash
grep -n "addUpgradeStatements\|DB_NAME\|DB_VERSION\|MIGRATIONS" src/app/shared/sqlite/app-settings.service.ts
```

**Verify**: `DB_NAME` is `'bubls'`, `DB_VERSION` is `1`, migrations array uses `{ version: number; statements: string[] }`. These are the patterns you must replicate.

**Critical note on migration versioning**: `AppSettingsService` already registered version 1 for the `'bubls'` database. The checkin migration MUST use version 2. The Capacitor SQLite plugin runs upgrade statements sequentially by version number. Using version 1 again would be a no-op (already applied) or a conflict. The version 2 migration must include ALL checkin table creation statements.

### Step 2: Add `checkin` mock flag to environment files

**Action**: Add `checkin: true` to the `useMocks` object in all three environment files. This gates the service to return mock data on web during development.

**File**: `src/environments/environment.ts`, `src/environments/environment.prod.ts`, `src/environments/environment.lan.ts`

**Pattern** (for `environment.ts`):
```typescript
useMocks: {
  picks: true,
  photoshoot: false,
  text: false,
  textChains: false,
  payments: true,
  checkin: true,          // <-- add this line
},
```

**Verify**: `npx tsc --noEmit` clean. All three files have the `checkin` key.

### Step 3: Create `checkin.model.ts` -- types, questions, qualities, thresholds

**Action**: Define all static data and TypeScript interfaces for the check-in domain. This file is pure data -- no Angular, no services, no side effects.

**File**: `src/app/pages/checkin/checkin.model.ts` (new)

**Pattern**:
```typescript
// ── Interfaces ────────────────────────────────────────────────────

export type Partner = 'A' | 'B';
export type SessionStatus = 'active' | 'complete' | 'expired';
export type QualityKey = 'communication' | 'respect' | 'prioritization' | 'viability';

export interface CheckinSession {
  id: string;
  created_at: string;
  status: SessionStatus;
  partner_a_submitted: boolean;
  partner_b_submitted: boolean;
}

export interface CheckinResponse {
  id: string;
  session_id: string;
  partner: Partner;
  question_index: number;
  score: number;
  submitted_at: string;
}

export interface CheckinQualityScore {
  id: string;
  session_id: string;
  partner: Partner;
  quality_key: QualityKey;
  score: number;
}

// ── Static Data ───────────────────────────────────────────────────

export interface CheckinQuestion {
  readonly index: number;
  readonly text: string;
  readonly qualityKey: QualityKey;
}

export const CHECKIN_QUESTIONS: readonly CheckinQuestion[] = [
  { index: 0, text: 'How honestly did we communicate today?', qualityKey: 'communication' },
  { index: 1, text: 'Did I feel safe saying what I really think?', qualityKey: 'communication' },
  { index: 2, text: 'How well did we listen to each other?', qualityKey: 'communication' },
  { index: 3, text: 'Did I feel respected during our time together?', qualityKey: 'respect' },
  { index: 4, text: 'Did we handle disagreements without dismissing each other?', qualityKey: 'respect' },
  { index: 5, text: 'Did I feel like a priority today?', qualityKey: 'prioritization' },
  { index: 6, text: 'Was our time together intentional, not just leftover?', qualityKey: 'prioritization' },
  { index: 7, text: 'Did today make me more confident about our future?', qualityKey: 'viability' },
  { index: 8, text: 'Are we growing in the same direction?', qualityKey: 'viability' },
  { index: 9, text: 'Would I want more days like today?', qualityKey: 'viability' },
] as const;

export interface QualityDefinition {
  readonly key: QualityKey;
  readonly displayName: string;
  readonly questionIndices: readonly number[];
}

export const QUALITY_DEFINITIONS: readonly QualityDefinition[] = [
  { key: 'communication', displayName: 'Communication Honesty', questionIndices: [0, 1, 2] },
  { key: 'respect', displayName: 'Mutual Respect', questionIndices: [3, 4] },
  { key: 'prioritization', displayName: 'Prioritization', questionIndices: [5, 6] },
  { key: 'viability', displayName: 'Long-term Viability', questionIndices: [7, 8, 9] },
] as const;

// ── Thresholds ────────────────────────────────────────────────────

export const THRESHOLD_HEALTHY = 7;
export const THRESHOLD_CONCERNING = 5;
export const DIVERGENCE_DELTA = 3;

// ── Result Types ──────────────────────────────────────────────────

export interface QualityResult {
  qualityKey: QualityKey;
  displayName: string;
  partnerAScore: number;
  partnerBScore: number;
  delta: number;
  isDivergent: boolean;
}

export interface SessionResult {
  session: CheckinSession;
  qualities: QualityResult[];
}

export interface QualityTrendPoint {
  sessionId: string;
  createdAt: string;
  partnerAScore: number;
  partnerBScore: number;
}

export interface QualityTrend {
  qualityKey: QualityKey;
  displayName: string;
  points: QualityTrendPoint[];
}
```

**Verify**: `npx tsc --noEmit` clean. File has zero imports from Angular or any service. Pure types and constants only.

### Step 4: Create `checkin.mock.ts` -- three mock sessions with divergent scores

**Action**: Define three complete mock sessions with realistic score data. Session 1: healthy and aligned. Session 2: divergent on communication. Session 3: one partner declining across all qualities. These fixtures serve both the mock mode in the service and test assertions.

**File**: `src/app/pages/checkin/checkin.mock.ts` (new)

**Pattern**:
```typescript
import {
  CheckinSession,
  CheckinResponse,
  CheckinQualityScore,
  QualityResult,
  SessionResult,
  QualityTrend,
  QUALITY_DEFINITIONS,
  DIVERGENCE_DELTA,
} from './checkin.model';

// ── Mock Sessions ─────────────────────────────────────────────────

export const MOCK_SESSIONS: CheckinSession[] = [
  {
    id: 'mock-session-1',
    created_at: '2026-04-10T19:00:00.000Z',
    status: 'complete',
    partner_a_submitted: true,
    partner_b_submitted: true,
  },
  {
    id: 'mock-session-2',
    created_at: '2026-04-13T20:00:00.000Z',
    status: 'complete',
    partner_a_submitted: true,
    partner_b_submitted: true,
  },
  {
    id: 'mock-session-3',
    created_at: '2026-04-16T18:30:00.000Z',
    status: 'complete',
    partner_a_submitted: true,
    partner_b_submitted: true,
  },
];

// Session 1: Healthy and aligned (scores 7-9, small deltas)
// Session 2: Divergent on communication (A=8, B=4 on Q0-Q2)
// Session 3: Partner B declining across all qualities

export const MOCK_QUALITY_SCORES: CheckinQualityScore[] = [
  // Session 1 — aligned
  { id: 'qs-1-a-comm', session_id: 'mock-session-1', partner: 'A', quality_key: 'communication', score: 8.0 },
  { id: 'qs-1-b-comm', session_id: 'mock-session-1', partner: 'B', quality_key: 'communication', score: 7.7 },
  { id: 'qs-1-a-resp', session_id: 'mock-session-1', partner: 'A', quality_key: 'respect', score: 8.5 },
  { id: 'qs-1-b-resp', session_id: 'mock-session-1', partner: 'B', quality_key: 'respect', score: 8.0 },
  { id: 'qs-1-a-prio', session_id: 'mock-session-1', partner: 'A', quality_key: 'prioritization', score: 7.5 },
  { id: 'qs-1-b-prio', session_id: 'mock-session-1', partner: 'B', quality_key: 'prioritization', score: 7.0 },
  { id: 'qs-1-a-viab', session_id: 'mock-session-1', partner: 'A', quality_key: 'viability', score: 8.3 },
  { id: 'qs-1-b-viab', session_id: 'mock-session-1', partner: 'B', quality_key: 'viability', score: 8.0 },
  // Session 2 — divergent communication
  { id: 'qs-2-a-comm', session_id: 'mock-session-2', partner: 'A', quality_key: 'communication', score: 8.0 },
  { id: 'qs-2-b-comm', session_id: 'mock-session-2', partner: 'B', quality_key: 'communication', score: 4.3 },
  { id: 'qs-2-a-resp', session_id: 'mock-session-2', partner: 'A', quality_key: 'respect', score: 7.5 },
  { id: 'qs-2-b-resp', session_id: 'mock-session-2', partner: 'B', quality_key: 'respect', score: 7.0 },
  { id: 'qs-2-a-prio', session_id: 'mock-session-2', partner: 'A', quality_key: 'prioritization', score: 7.0 },
  { id: 'qs-2-b-prio', session_id: 'mock-session-2', partner: 'B', quality_key: 'prioritization', score: 6.5 },
  { id: 'qs-2-a-viab', session_id: 'mock-session-2', partner: 'A', quality_key: 'viability', score: 7.7 },
  { id: 'qs-2-b-viab', session_id: 'mock-session-2', partner: 'B', quality_key: 'viability', score: 7.3 },
  // Session 3 — Partner B declining
  { id: 'qs-3-a-comm', session_id: 'mock-session-3', partner: 'A', quality_key: 'communication', score: 8.0 },
  { id: 'qs-3-b-comm', session_id: 'mock-session-3', partner: 'B', quality_key: 'communication', score: 4.0 },
  { id: 'qs-3-a-resp', session_id: 'mock-session-3', partner: 'A', quality_key: 'respect', score: 7.5 },
  { id: 'qs-3-b-resp', session_id: 'mock-session-3', partner: 'B', quality_key: 'respect', score: 4.5 },
  { id: 'qs-3-a-prio', session_id: 'mock-session-3', partner: 'A', quality_key: 'prioritization', score: 7.0 },
  { id: 'qs-3-b-prio', session_id: 'mock-session-3', partner: 'B', quality_key: 'prioritization', score: 4.0 },
  { id: 'qs-3-a-viab', session_id: 'mock-session-3', partner: 'A', quality_key: 'viability', score: 7.7 },
  { id: 'qs-3-b-viab', session_id: 'mock-session-3', partner: 'B', quality_key: 'viability', score: 3.7 },
];

// ── Computed mock results (for mock service returns) ──────────────

function buildMockResults(sessionId: string): QualityResult[] {
  return QUALITY_DEFINITIONS.map((qd) => {
    const aScore = MOCK_QUALITY_SCORES.find(
      (qs) => qs.session_id === sessionId && qs.partner === 'A' && qs.quality_key === qd.key,
    );
    const bScore = MOCK_QUALITY_SCORES.find(
      (qs) => qs.session_id === sessionId && qs.partner === 'B' && qs.quality_key === qd.key,
    );
    const a = aScore?.score ?? 0;
    const b = bScore?.score ?? 0;
    const delta = Math.abs(a - b);
    return {
      qualityKey: qd.key,
      displayName: qd.displayName,
      partnerAScore: a,
      partnerBScore: b,
      delta: Math.round(delta * 10) / 10,
      isDivergent: delta >= DIVERGENCE_DELTA,
    };
  });
}

export const MOCK_SESSION_RESULTS: SessionResult[] = MOCK_SESSIONS.map((s) => ({
  session: s,
  qualities: buildMockResults(s.id),
}));

export const MOCK_QUALITY_TRENDS: QualityTrend[] = QUALITY_DEFINITIONS.map((qd) => ({
  qualityKey: qd.key,
  displayName: qd.displayName,
  points: MOCK_SESSIONS.map((s) => {
    const a = MOCK_QUALITY_SCORES.find(
      (qs) => qs.session_id === s.id && qs.partner === 'A' && qs.quality_key === qd.key,
    );
    const b = MOCK_QUALITY_SCORES.find(
      (qs) => qs.session_id === s.id && qs.partner === 'B' && qs.quality_key === qd.key,
    );
    return {
      sessionId: s.id,
      createdAt: s.created_at,
      partnerAScore: a?.score ?? 0,
      partnerBScore: b?.score ?? 0,
    };
  }),
}));

export const MOCK_ACTIVE_SESSION: CheckinSession = {
  id: 'mock-active',
  created_at: new Date().toISOString(),
  status: 'active',
  partner_a_submitted: false,
  partner_b_submitted: false,
};
```

**Verify**: `npx tsc --noEmit` clean. Mock data is self-consistent (every session ID referenced in quality scores exists in sessions).

### Step 5: Create `checkin.service.ts` -- the adapter

**Action**: Build the service following the `AppSettingsService` pattern: inject `SqliteService`, define migrations, expose typed methods. Mock mode reads from `environment.useMocks.checkin`. Real mode reads/writes SQLite. Quality score computation happens inside `submitResponses()` -- compute the average per quality from the raw scores, then write to `checkin_quality_score`.

**File**: `src/app/pages/checkin/checkin.service.ts` (new)

**Pattern**:
```typescript
import { Injectable, inject } from '@angular/core';

import { SqliteService } from '../../shared/sqlite/sqlite.service';
import type { Migration } from '../../shared/sqlite/sqlite.model';
import { environment } from '../../../environments/environment';
import {
  Partner,
  CheckinSession,
  CheckinQualityScore,
  SessionResult,
  QualityResult,
  QualityTrend,
  QualityTrendPoint,
  CHECKIN_QUESTIONS,
  QUALITY_DEFINITIONS,
  DIVERGENCE_DELTA,
} from './checkin.model';
import {
  MOCK_SESSIONS,
  MOCK_ACTIVE_SESSION,
  MOCK_SESSION_RESULTS,
  MOCK_QUALITY_TRENDS,
} from './checkin.mock';

const DB_NAME = 'bubls';

/**
 * Migration version 2 — adds checkin tables to the shared bubls database.
 *
 * Version 1 is already claimed by AppSettingsService (app_settings table).
 * This MUST be version 2 to avoid conflicting with the existing migration.
 */
const CHECKIN_MIGRATIONS: Migration[] = [
  {
    version: 2,
    statements: [
      `CREATE TABLE IF NOT EXISTS checkin_session (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        partner_a_submitted INTEGER NOT NULL DEFAULT 0,
        partner_b_submitted INTEGER NOT NULL DEFAULT 0
      );`,
      `CREATE TABLE IF NOT EXISTS checkin_response (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        partner TEXT NOT NULL,
        question_index INTEGER NOT NULL,
        score INTEGER NOT NULL,
        submitted_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES checkin_session(id)
      );`,
      `CREATE TABLE IF NOT EXISTS checkin_quality_score (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        partner TEXT NOT NULL,
        quality_key TEXT NOT NULL,
        score REAL NOT NULL,
        FOREIGN KEY (session_id) REFERENCES checkin_session(id)
      );`,
    ],
  },
];

/** Row shape from checkin_session SELECT. SQLite returns INTEGER as number. */
interface SessionRow {
  id: string;
  created_at: string;
  status: string;
  partner_a_submitted: number;
  partner_b_submitted: number;
}

/** Row shape from checkin_quality_score SELECT. */
interface QualityScoreRow {
  id: string;
  session_id: string;
  partner: string;
  quality_key: string;
  score: number;
}

@Injectable({ providedIn: 'root' })
export class CheckinService {
  private readonly sqlite = inject(SqliteService);
  private initialized = false;
  private readonly useMock = environment.useMocks.checkin;

  // ── Initialization ──────────────────────────────────────────────

  /**
   * Register checkin migrations and warm up the database.
   * Safe to call multiple times -- only the first call executes.
   */
  async init(): Promise<void> {
    if (this.initialized || this.useMock) {
      this.initialized = true;
      return;
    }

    await this.sqlite.addUpgradeStatements(DB_NAME, CHECKIN_MIGRATIONS);
    await this.sqlite.query<SessionRow>({
      database: DB_NAME,
      statement: 'SELECT id FROM checkin_session LIMIT 1;',
    });
    this.initialized = true;
  }

  // ── Session Management ──────────────────────────────────────────

  async createSession(): Promise<CheckinSession> {
    const session: CheckinSession = {
      id: crypto.randomUUID(),
      created_at: new Date().toISOString(),
      status: 'active',
      partner_a_submitted: false,
      partner_b_submitted: false,
    };

    if (this.useMock) {
      return { ...MOCK_ACTIVE_SESSION, id: session.id, created_at: session.created_at };
    }

    await this.init();
    await this.sqlite.execute({
      database: DB_NAME,
      statement:
        'INSERT INTO checkin_session (id, created_at, status, partner_a_submitted, partner_b_submitted) VALUES (?, ?, ?, 0, 0);',
      values: [session.id, session.created_at, 'active'],
    });
    return session;
  }

  async getActiveSession(): Promise<CheckinSession | null> {
    if (this.useMock) {
      return { ...MOCK_ACTIVE_SESSION };
    }

    await this.init();
    const result = await this.sqlite.query<SessionRow>({
      database: DB_NAME,
      statement: "SELECT * FROM checkin_session WHERE status = 'active' ORDER BY created_at DESC LIMIT 1;",
    });

    if (result.values.length === 0) {
      return null;
    }
    return this.mapSessionRow(result.values[0]);
  }

  // ── Response Submission ─────────────────────────────────────────

  /**
   * Submit all ten responses for a partner and compute quality scores.
   *
   * @param sessionId - The active session ID
   * @param partner - 'A' or 'B'
   * @param scores - Array of exactly 10 scores (index matches question_index)
   */
  async submitResponses(
    sessionId: string,
    partner: Partner,
    scores: number[],
  ): Promise<void> {
    if (scores.length !== CHECKIN_QUESTIONS.length) {
      throw new Error(
        `Expected ${CHECKIN_QUESTIONS.length} scores, got ${scores.length}`,
      );
    }

    if (this.useMock) {
      return;
    }

    await this.init();
    const now = new Date().toISOString();

    // Write individual responses
    for (let i = 0; i < scores.length; i++) {
      await this.sqlite.execute({
        database: DB_NAME,
        statement:
          'INSERT INTO checkin_response (id, session_id, partner, question_index, score, submitted_at) VALUES (?, ?, ?, ?, ?, ?);',
        values: [crypto.randomUUID(), sessionId, partner, i, scores[i], now],
      });
    }

    // Compute and write quality scores
    for (const quality of QUALITY_DEFINITIONS) {
      const qualityScores = quality.questionIndices.map((qi) => scores[qi]);
      const avg = qualityScores.reduce((sum, s) => sum + s, 0) / qualityScores.length;
      const rounded = Math.round(avg * 10) / 10;

      await this.sqlite.execute({
        database: DB_NAME,
        statement:
          'INSERT INTO checkin_quality_score (id, session_id, partner, quality_key, score) VALUES (?, ?, ?, ?, ?);',
        values: [crypto.randomUUID(), sessionId, partner, quality.key, rounded],
      });
    }

    // Mark partner as submitted
    const column = partner === 'A' ? 'partner_a_submitted' : 'partner_b_submitted';
    await this.sqlite.execute({
      database: DB_NAME,
      statement: `UPDATE checkin_session SET ${column} = 1 WHERE id = ?;`,
      values: [sessionId],
    });

    // Check if both submitted -- if so, mark complete
    const session = await this.sqlite.query<SessionRow>({
      database: DB_NAME,
      statement: 'SELECT * FROM checkin_session WHERE id = ?;',
      values: [sessionId],
    });
    if (
      session.values.length > 0 &&
      session.values[0].partner_a_submitted === 1 &&
      session.values[0].partner_b_submitted === 1
    ) {
      await this.sqlite.execute({
        database: DB_NAME,
        statement: "UPDATE checkin_session SET status = 'complete' WHERE id = ?;",
        values: [sessionId],
      });
    }
  }

  // ── Results ─────────────────────────────────────────────────────

  /**
   * Get results for a completed session. Returns null if session
   * is not complete (privacy: no partial score leaking).
   */
  async getSessionResults(sessionId: string): Promise<SessionResult | null> {
    if (this.useMock) {
      return MOCK_SESSION_RESULTS.find((r) => r.session.id === sessionId) ?? null;
    }

    await this.init();
    const sessionResult = await this.sqlite.query<SessionRow>({
      database: DB_NAME,
      statement: 'SELECT * FROM checkin_session WHERE id = ?;',
      values: [sessionId],
    });

    if (sessionResult.values.length === 0) {
      return null;
    }

    const session = this.mapSessionRow(sessionResult.values[0]);
    if (session.status !== 'complete') {
      return null;
    }

    const qualityRows = await this.sqlite.query<QualityScoreRow>({
      database: DB_NAME,
      statement: 'SELECT * FROM checkin_quality_score WHERE session_id = ?;',
      values: [sessionId],
    });

    const qualities: QualityResult[] = QUALITY_DEFINITIONS.map((qd) => {
      const aRow = qualityRows.values.find(
        (r) => r.partner === 'A' && r.quality_key === qd.key,
      );
      const bRow = qualityRows.values.find(
        (r) => r.partner === 'B' && r.quality_key === qd.key,
      );
      const a = aRow?.score ?? 0;
      const b = bRow?.score ?? 0;
      const delta = Math.round(Math.abs(a - b) * 10) / 10;
      return {
        qualityKey: qd.key,
        displayName: qd.displayName,
        partnerAScore: a,
        partnerBScore: b,
        delta,
        isDivergent: delta >= DIVERGENCE_DELTA,
      };
    });

    return { session, qualities };
  }

  // ── Trends ──────────────────────────────────────────────────────

  /**
   * Get quality score trends across the last N completed sessions.
   */
  async getQualityTrends(limit: number = 10): Promise<QualityTrend[]> {
    if (this.useMock) {
      return MOCK_QUALITY_TRENDS;
    }

    await this.init();
    const sessions = await this.sqlite.query<SessionRow>({
      database: DB_NAME,
      statement:
        "SELECT * FROM checkin_session WHERE status = 'complete' ORDER BY created_at DESC LIMIT ?;",
      values: [limit],
    });

    // Reverse so oldest is first (chronological order for charts)
    const orderedSessions = sessions.values.reverse();

    if (orderedSessions.length === 0) {
      return QUALITY_DEFINITIONS.map((qd) => ({
        qualityKey: qd.key,
        displayName: qd.displayName,
        points: [],
      }));
    }

    const sessionIds = orderedSessions.map((s) => s.id);
    const placeholders = sessionIds.map(() => '?').join(',');
    const allScores = await this.sqlite.query<QualityScoreRow>({
      database: DB_NAME,
      statement: `SELECT * FROM checkin_quality_score WHERE session_id IN (${placeholders});`,
      values: sessionIds,
    });

    return QUALITY_DEFINITIONS.map((qd) => ({
      qualityKey: qd.key,
      displayName: qd.displayName,
      points: orderedSessions.map((s): QualityTrendPoint => {
        const a = allScores.values.find(
          (r) => r.session_id === s.id && r.partner === 'A' && r.quality_key === qd.key,
        );
        const b = allScores.values.find(
          (r) => r.session_id === s.id && r.partner === 'B' && r.quality_key === qd.key,
        );
        return {
          sessionId: s.id,
          createdAt: s.created_at,
          partnerAScore: a?.score ?? 0,
          partnerBScore: b?.score ?? 0,
        };
      }),
    }));
  }

  // ── Expiry ──────────────────────────────────────────────────────

  /**
   * Expire sessions older than 48 hours where only one partner submitted.
   * Called on app open / route activation.
   */
  async expireStale(): Promise<number> {
    if (this.useMock) {
      return 0;
    }

    await this.init();
    const cutoff = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString();
    const stale = await this.sqlite.query<SessionRow>({
      database: DB_NAME,
      statement:
        "SELECT id FROM checkin_session WHERE status = 'active' AND created_at < ?;",
      values: [cutoff],
    });

    for (const row of stale.values) {
      await this.sqlite.execute({
        database: DB_NAME,
        statement: "UPDATE checkin_session SET status = 'expired' WHERE id = ?;",
        values: [row.id],
      });
    }

    return stale.values.length;
  }

  // ── Completed Sessions List ─────────────────────────────────────

  /**
   * Get all completed sessions for the history list, newest first.
   */
  async getCompletedSessions(): Promise<CheckinSession[]> {
    if (this.useMock) {
      return [...MOCK_SESSIONS];
    }

    await this.init();
    const result = await this.sqlite.query<SessionRow>({
      database: DB_NAME,
      statement:
        "SELECT * FROM checkin_session WHERE status = 'complete' ORDER BY created_at DESC;",
    });
    return result.values.map(this.mapSessionRow);
  }

  // ── Private Helpers ─────────────────────────────────────────────

  private mapSessionRow(row: SessionRow): CheckinSession {
    return {
      id: row.id,
      created_at: row.created_at,
      status: row.status as CheckinSession['status'],
      partner_a_submitted: row.partner_a_submitted === 1,
      partner_b_submitted: row.partner_b_submitted === 1,
    };
  }
}
```

**Key decisions embedded in the code**:
- Migration version is 2 (version 1 is `app_settings`).
- `submitResponses()` is transactional in intent: writes responses, computes quality averages, marks partner submitted, and auto-transitions to `complete` if both done. Capacitor SQLite does not support explicit transactions via this wrapper, so each statement is atomic. The worst case (crash between response write and quality write) leaves orphan responses that are harmless -- the session stays `active` and the partner can re-submit (idempotency is Task 6's concern; here we document the gap).
- `getSessionResults()` returns `null` for non-complete sessions. This is the privacy model: no score leaking.
- `expireStale()` uses ISO string comparison for the 48h cutoff. SQLite sorts ISO 8601 strings lexicographically correctly.

**Verify**: `npx tsc --noEmit` clean. Service file size is under 250 lines.

### Step 6: Write unit tests

**Action**: Create the spec file following the `AppSettingsService` test pattern: mock `SqliteService` with jasmine spyObj, control return values, assert the correct SQL statements and values are passed.

**File**: `src/app/pages/checkin/checkin.service.spec.ts` (new)

See section 5 for full test bodies.

**Verify**: `npm test -- --watch=false --browsers=ChromeHeadless` -- all new tests green, no pre-existing tests regressed.

---

## 5. Tests

Framework: Jasmine + Karma (repo convention). Mock pattern: `jasmine.createSpyObj<SqliteService>` with controlled return values, matching the `AppSettingsService` spec at `src/app/shared/sqlite/app-settings.service.spec.ts`.

### `src/app/pages/checkin/checkin.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';

import { CheckinService } from './checkin.service';
import { SqliteService } from '../../shared/sqlite/sqlite.service';
import { CHECKIN_QUESTIONS, QUALITY_DEFINITIONS } from './checkin.model';

/**
 * Unit tests for CheckinService.
 *
 * Uses a mock SqliteService that tracks calls and returns
 * controlled results. No native plugin involved.
 *
 * Note: these tests set environment.useMocks.checkin = false
 * to test the real SQLite code paths. Tests for mock mode
 * are separate.
 */
describe('CheckinService', () => {
  let service: CheckinService;
  let sqliteSpy: jasmine.SpyObj<SqliteService>;

  beforeEach(() => {
    sqliteSpy = jasmine.createSpyObj('SqliteService', [
      'addUpgradeStatements',
      'query',
      'execute',
    ]);

    sqliteSpy.addUpgradeStatements.and.resolveTo();
    sqliteSpy.query.and.resolveTo({ values: [] });
    sqliteSpy.execute.and.resolveTo();

    TestBed.configureTestingModule({
      providers: [
        CheckinService,
        { provide: SqliteService, useValue: sqliteSpy },
      ],
    });

    service = TestBed.inject(CheckinService);
    // Force non-mock mode for SQLite path testing.
    // The service reads environment.useMocks.checkin at construction,
    // so override the private field for test isolation.
    (service as any).useMock = false;
    (service as any).initialized = false;
  });

  // ── init ────────────────────────────────────────────────────────

  it('init_registersMigrationsWithVersion2', async () => {
    await service.init();

    expect(sqliteSpy.addUpgradeStatements).toHaveBeenCalledOnceWith(
      'bubls',
      jasmine.arrayContaining([
        jasmine.objectContaining({ version: 2 }),
      ]),
    );
  });

  it('init_calledTwice_onlyExecutesOnce', async () => {
    await service.init();
    await service.init();

    expect(sqliteSpy.addUpgradeStatements).toHaveBeenCalledTimes(1);
  });

  // ── createSession ───────────────────────────────────────────────

  it('createSession_insertsRowWithActiveStatus', async () => {
    const session = await service.createSession();

    expect(session.status).toBe('active');
    expect(session.partner_a_submitted).toBeFalse();
    expect(session.partner_b_submitted).toBeFalse();
    expect(session.id).toBeTruthy();
    expect(sqliteSpy.execute).toHaveBeenCalledWith(
      jasmine.objectContaining({
        database: 'bubls',
        statement: jasmine.stringContaining('INSERT INTO checkin_session'),
      }),
    );
  });

  // ── getActiveSession ────────────────────────────────────────────

  it('getActiveSession_noActive_returnsNull', async () => {
    sqliteSpy.query.and.resolveTo({ values: [] });

    const result = await service.getActiveSession();

    expect(result).toBeNull();
  });

  it('getActiveSession_hasActive_returnsSession', async () => {
    sqliteSpy.query.and.callFake(async (opts: any) => {
      if (opts.statement.includes('checkin_session LIMIT 1')) {
        // init warmup query
        return { values: [] };
      }
      return {
        values: [{
          id: 'sess-1',
          created_at: '2026-04-16T18:00:00.000Z',
          status: 'active',
          partner_a_submitted: 0,
          partner_b_submitted: 0,
        }],
      };
    });

    const result = await service.getActiveSession();

    expect(result).toBeTruthy();
    expect(result!.id).toBe('sess-1');
    expect(result!.partner_a_submitted).toBeFalse();
  });

  // ── submitResponses ─────────────────────────────────────────────

  it('submitResponses_wrongScoreCount_throws', async () => {
    await expectAsync(
      service.submitResponses('sess-1', 'A', [1, 2, 3]),
    ).toBeRejectedWithError(/Expected 10 scores, got 3/);
  });

  it('submitResponses_writesResponsesAndQualityScores', async () => {
    const scores = [8, 7, 9, 8, 7, 6, 7, 8, 9, 8];

    // Mock the session query for auto-complete check
    sqliteSpy.query.and.resolveTo({
      values: [{
        id: 'sess-1',
        created_at: '2026-04-16T18:00:00.000Z',
        status: 'active',
        partner_a_submitted: 1,
        partner_b_submitted: 0,
      }],
    });

    await service.submitResponses('sess-1', 'A', scores);

    // 10 response inserts + 4 quality score inserts + 1 partner update = 15 execute calls
    // Plus the init warmup (0 or 1 depending on state)
    const responseCalls = sqliteSpy.execute.calls
      .allArgs()
      .filter((args: any) => args[0].statement.includes('INSERT INTO checkin_response'));
    expect(responseCalls.length).toBe(10);

    const qualityCalls = sqliteSpy.execute.calls
      .allArgs()
      .filter((args: any) => args[0].statement.includes('INSERT INTO checkin_quality_score'));
    expect(qualityCalls.length).toBe(4);
  });

  it('submitResponses_bothSubmitted_marksSessionComplete', async () => {
    const scores = [8, 7, 9, 8, 7, 6, 7, 8, 9, 8];

    // Session query returns both submitted after the update
    sqliteSpy.query.and.resolveTo({
      values: [{
        id: 'sess-1',
        created_at: '2026-04-16T18:00:00.000Z',
        status: 'active',
        partner_a_submitted: 1,
        partner_b_submitted: 1,
      }],
    });

    await service.submitResponses('sess-1', 'B', scores);

    const completeCalls = sqliteSpy.execute.calls
      .allArgs()
      .filter((args: any) => args[0].statement.includes("status = 'complete'"));
    expect(completeCalls.length).toBe(1);
  });

  // ── getSessionResults ───────────────────────────────────────────

  it('getSessionResults_incompleteSession_returnsNull', async () => {
    sqliteSpy.query.and.callFake(async (opts: any) => {
      if (opts.statement.includes('checkin_session WHERE id')) {
        return {
          values: [{
            id: 'sess-1',
            created_at: '2026-04-16T18:00:00.000Z',
            status: 'active',
            partner_a_submitted: 1,
            partner_b_submitted: 0,
          }],
        };
      }
      return { values: [] };
    });

    const result = await service.getSessionResults('sess-1');

    expect(result).toBeNull();
  });

  it('getSessionResults_completeSession_returnsQualityResults', async () => {
    sqliteSpy.query.and.callFake(async (opts: any) => {
      if (opts.statement.includes('checkin_session WHERE id')) {
        return {
          values: [{
            id: 'sess-1',
            created_at: '2026-04-16T18:00:00.000Z',
            status: 'complete',
            partner_a_submitted: 1,
            partner_b_submitted: 1,
          }],
        };
      }
      if (opts.statement.includes('checkin_quality_score')) {
        return {
          values: [
            { id: 'qs-1', session_id: 'sess-1', partner: 'A', quality_key: 'communication', score: 8.0 },
            { id: 'qs-2', session_id: 'sess-1', partner: 'B', quality_key: 'communication', score: 5.0 },
            { id: 'qs-3', session_id: 'sess-1', partner: 'A', quality_key: 'respect', score: 7.0 },
            { id: 'qs-4', session_id: 'sess-1', partner: 'B', quality_key: 'respect', score: 7.0 },
            { id: 'qs-5', session_id: 'sess-1', partner: 'A', quality_key: 'prioritization', score: 6.0 },
            { id: 'qs-6', session_id: 'sess-1', partner: 'B', quality_key: 'prioritization', score: 6.0 },
            { id: 'qs-7', session_id: 'sess-1', partner: 'A', quality_key: 'viability', score: 8.0 },
            { id: 'qs-8', session_id: 'sess-1', partner: 'B', quality_key: 'viability', score: 8.0 },
          ],
        };
      }
      return { values: [] };
    });

    const result = await service.getSessionResults('sess-1');

    expect(result).toBeTruthy();
    expect(result!.qualities.length).toBe(4);

    const comm = result!.qualities.find((q) => q.qualityKey === 'communication');
    expect(comm!.partnerAScore).toBe(8.0);
    expect(comm!.partnerBScore).toBe(5.0);
    expect(comm!.delta).toBe(3.0);
    expect(comm!.isDivergent).toBeTrue();

    const respect = result!.qualities.find((q) => q.qualityKey === 'respect');
    expect(respect!.delta).toBe(0);
    expect(respect!.isDivergent).toBeFalse();
  });

  // ── expireStale ─────────────────────────────────────────────────

  it('expireStale_noStale_returnsZero', async () => {
    sqliteSpy.query.and.resolveTo({ values: [] });

    const count = await service.expireStale();

    expect(count).toBe(0);
  });

  it('expireStale_staleExists_expiresAndReturnsCount', async () => {
    sqliteSpy.query.and.callFake(async (opts: any) => {
      if (opts.statement.includes("status = 'active' AND created_at")) {
        return {
          values: [
            { id: 'old-1' },
            { id: 'old-2' },
          ],
        };
      }
      return { values: [] };
    });

    const count = await service.expireStale();

    expect(count).toBe(2);
    const expireCalls = sqliteSpy.execute.calls
      .allArgs()
      .filter((args: any) => args[0].statement.includes("status = 'expired'"));
    expect(expireCalls.length).toBe(2);
  });

  // ── getCompletedSessions ────────────────────────────────────────

  it('getCompletedSessions_returnsCompletedOnly', async () => {
    sqliteSpy.query.and.callFake(async (opts: any) => {
      if (opts.statement.includes("status = 'complete'")) {
        return {
          values: [
            {
              id: 'sess-1',
              created_at: '2026-04-16T18:00:00.000Z',
              status: 'complete',
              partner_a_submitted: 1,
              partner_b_submitted: 1,
            },
          ],
        };
      }
      return { values: [] };
    });

    const sessions = await service.getCompletedSessions();

    expect(sessions.length).toBe(1);
    expect(sessions[0].status).toBe('complete');
    expect(sessions[0].partner_a_submitted).toBeTrue();
  });

  // ── Quality computation correctness ─────────────────────────────

  it('submitResponses_qualityAveragesComputedCorrectly', async () => {
    // Scores: communication (Q0=8, Q1=6, Q2=7) → avg 7.0
    //         respect (Q3=9, Q4=5) → avg 7.0
    //         prioritization (Q5=4, Q6=6) → avg 5.0
    //         viability (Q7=8, Q8=9, Q9=7) → avg 8.0
    const scores = [8, 6, 7, 9, 5, 4, 6, 8, 9, 7];

    sqliteSpy.query.and.resolveTo({
      values: [{
        id: 'sess-1',
        created_at: '2026-04-16T18:00:00.000Z',
        status: 'active',
        partner_a_submitted: 1,
        partner_b_submitted: 0,
      }],
    });

    await service.submitResponses('sess-1', 'A', scores);

    const qualityCalls = sqliteSpy.execute.calls
      .allArgs()
      .filter((args: any) => args[0].statement.includes('INSERT INTO checkin_quality_score'))
      .map((args: any) => ({
        qualityKey: args[0].values[3],
        score: args[0].values[4],
      }));

    const comm = qualityCalls.find((c: any) => c.qualityKey === 'communication');
    expect(comm!.score).toBe(7.0);

    const respect = qualityCalls.find((c: any) => c.qualityKey === 'respect');
    expect(respect!.score).toBe(7.0);

    const prio = qualityCalls.find((c: any) => c.qualityKey === 'prioritization');
    expect(prio!.score).toBe(5.0);

    const viab = qualityCalls.find((c: any) => c.qualityKey === 'viability');
    expect(viab!.score).toBe(8.0);
  });
});
```

### Model assertions (inline in model file -- no spec needed)

The model file is pure types and constants with no logic. Validate at compile time via `npx tsc --noEmit`. No spec file needed -- if the types are wrong, downstream service tests fail.

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(checkin): add checkin mock flag to environment files` -- `src/environments/environment.ts`, `environment.prod.ts`, `environment.lan.ts`: add `checkin: true` to `useMocks`.
2. `feat(checkin): define model types, questions, qualities, and thresholds` -- `src/app/pages/checkin/checkin.model.ts`: interfaces, static data, threshold constants.
3. `feat(checkin): add mock data for three check-in sessions` -- `src/app/pages/checkin/checkin.mock.ts`: three sessions with divergent scores, computed results and trends.
4. `feat(checkin): SQLite schema migration and data service adapter` -- `src/app/pages/checkin/checkin.service.ts`: version 2 migration (three tables), full CRUD service with mock mode.
5. `test(checkin): unit tests for CheckinService` -- `src/app/pages/checkin/checkin.service.spec.ts`: assertions for init, create, submit, results, expiry, quality computation.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation. Keep the total to 3 or fewer per commit.

---

## 7. Verification

```bash
npm test -- --watch=false --browsers=ChromeHeadless
npm run build
```

**Expected delta**: `N` (baseline from section 2) to `N + 12` passing (12 new `CheckinService` specs). Zero pre-existing tests broken. `npm run build` clean with no new warnings.

**Manual check**: import `CheckinService` in a throwaway `main.ts` snippet and call `createSession()` in the browser console to confirm mock mode returns a session object with a UUID id and `'active'` status. Remove the throwaway code before committing.

**Type check**: `npx tsc --noEmit` must pass with zero errors. The model types are consumed by the service and tests -- a type mismatch surfaces immediately.

---

## 8. Rollback

- **Per-step**: each of the 5 commits is independently revertible. `git revert <sha>` on any single commit restores the prior state.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` (record the SHA during section 2 Pre-flight) or delete the feature branch.
- **Environment flag safety**: if the `useMocks.checkin` flag causes type errors in unrelated code (because the environment interface changed shape), revert commit 1 and instead use a service-local boolean constant until the environment interface can be extended safely.

---

## 9. Deviations Allowed

- **Migration version conflict** -- if `AppSettingsService` has moved beyond version 1 since the architecture was written, use the next available version number. Inspect `app-settings.service.ts` and any other SQLite consumers to determine the current max version. Log the actual version used in the commit body.
- **Environment file structure differs** -- if `environment.ts` does not have a `useMocks` object (structure changed since last read), define a top-level `MOCK_CHECKIN = true` constant inside `checkin.service.ts` instead. Log as deviation.
- **`crypto.randomUUID()` unavailable** -- if the build target does not support `crypto.randomUUID()` (check `tsconfig.json` lib array), use a simple `Date.now().toString(36) + Math.random().toString(36).slice(2)` fallback. Log as deviation.
- **Capacitor SQLite plugin not installed** -- if `@capacitor-community/sqlite` is missing from `package.json`, the `SqliteService` will no-op on web (which is fine for mock mode). Do NOT install the plugin in this task. Log as deviation and note that native testing requires the plugin.
- **Existing `checkin/` directory** -- if `src/app/pages/checkin/` already exists with conflicting files, STOP and flag. Do not overwrite.
- **Test framework mismatch** -- if existing specs use Jest/Vitest instead of Jasmine, translate assertions to match the actual framework. Log as deviation.
- **Side-effect required** (push, publish, schema change on real device) -- STOP, mark `[REQUIRES APPROVAL]`, ask.

---

## 10. Out of Scope

This task creates the persistence layer and data service -- nothing more. It does NOT build any UI component, register any route, modify the shell, or create page-level files.

- **Route registration** -- `app.routes.ts` modification belongs to Task 2. Do not add a `/checkin` route here.
- **Page component** (`checkin.page.ts`) -- Task 2 owns the entry screen.
- **Rating UI** (`checkin-rate.component.ts`, `score-selector.component.ts`) -- Task 3.
- **Results/waiting views** -- Task 4.
- **Trend charts** (`sparkline.component.ts`) -- Task 5.
- **Session expiry on app open** (wiring `expireStale()` into a route guard or app initializer) -- Task 6. The method exists in the service but is not called anywhere yet.
- **Draft persistence** (`checkin_draft` table for crash recovery) -- Task 6. The architecture mentions it; this task does not build it.
- **Idempotent submit guard** (preventing double-submit of the same partner) -- Task 6. The service currently allows duplicate inserts.
- **Shell tab bar entry** -- Task 2.
- **Any visual styling or CSS** -- downstream tasks.
- **Backend / server changes** -- this feature is local-only, no server code.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) -- Design rationale, table schemas, component design
- [Epic](./epic.md) -- Task scope and dependencies
- [Analysis](./analysis.md) -- Problem statement and open questions
- [Timeline](./timeline.md) -- Status tracking (update after done)
