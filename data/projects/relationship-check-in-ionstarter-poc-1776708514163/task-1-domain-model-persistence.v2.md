# Task 1: Domain Models + Persistence Layer

## 1. Purpose

Define the check-in data models and implement the dual-backend persistence services (SQLite for native, Capacitor Preferences for web) mirroring ionstarter's tasks domain pattern exactly.

---

## 2. Metadata Block

| Field | Value |
|-------|-------|
| **Effort** | 1 day |
| **Dependencies** | None |
| **Parallel with** | Nothing (this is the foundation) |
| **Blocks** | Task 2 (session creation), Task 3 (rating UI), all subsequent tasks |

---

## 3. Context

### Why this task exists

The check-in domain needs persistence before any UI can be built. Ionstarter already has a proven dual-backend pattern in its tasks domain: `TasksSqliteService` for native platforms using `@capacitor-community/sqlite`, `TasksLocalStorageService` for web using `@capacitor/preferences`, and `TasksService` that routes between them based on `Capacitor.getPlatform()`. This task replicates that exact pattern for check-in data (sessions and responses).

### Trade-offs

- **Separate services per backend instead of a single adaptive service**: The tasks domain uses three separate services rather than one service with internal branching. This adds files but makes each service trivially testable and follows the established pattern. We mirror this choice.
- **SQLite database name `check-in` instead of sharing the `tasks` database**: Each domain owns its own database name. This avoids migration version conflicts between domains and matches ionstarter's isolation principle.
- **`nanoid()` for IDs instead of `crypto.randomUUID()`**: The tasks domain uses `nanoid()` in its `TasksService`. We follow the same convention. The bubls codebase uses `crypto.randomUUID()`, but ionstarter's pattern takes precedence.
- **Constructor-based DI instead of `inject()`**: The tasks domain uses constructor injection (`private readonly`). We mirror that pattern even though the architecture principles mention `inject()`.
- **Flat service files in service subdirectories**: Ionstarter puts each service in its own subdirectory (`services/tasks-sqlite/tasks-sqlite.service.ts`). We follow this convention.

### Rejected alternatives

- **Single `CheckInDataService` (bubls pattern)**: Bubls combines all persistence into one service with direct SQLite calls and web no-ops. Ionstarter separates concerns into sqlite/localStorage/routing layers. We follow ionstarter.
- **Abstract persistence interface**: The architecture doc explicitly says "No new abstractions." We use concrete services with matching method signatures.

---

## 4. Pre-flight

Run from the ionstarter project root (`/projects/ionstarter/`):

```bash
# 1. Verify the project builds cleanly before touching anything
cd /projects/ionstarter && npm run build

# 2. Verify tests pass
cd /projects/ionstarter && npm run test:ci

# 3. Confirm nanoid is installed
node -e "const p = require('./package.json'); console.log('nanoid:', p.dependencies['nanoid'])"
# Expected: nanoid: 5.0.7

# 4. Confirm @capacitor-community/sqlite is installed
node -e "const p = require('./package.json'); console.log('sqlite:', p.dependencies['@capacitor-community/sqlite'])"
# Expected: sqlite: 7.0.0

# 5. Verify the tasks domain reference files exist
ls src/app/domains/tasks/services/tasks-sqlite/tasks-sqlite.service.ts
ls src/app/domains/tasks/services/tasks-local-storage/tasks-local-storage.service.ts
ls src/app/domains/tasks/services/tasks/tasks.service.ts
ls src/app/domains/tasks/interfaces/task.ts

# 6. Create the domain directory scaffold
mkdir -p src/app/domains/check-in/interfaces
mkdir -p src/app/domains/check-in/services/check-in-sqlite
mkdir -p src/app/domains/check-in/services/check-in-local-storage
mkdir -p src/app/domains/check-in/services/check-in
```

---

## 5. Files

### To Create

| # | Path | Purpose |
|---|------|---------|
| 1 | `src/app/domains/check-in/interfaces/check-in.ts` | All domain interfaces (CheckInSession, CheckInResponse, QualityScore, CompletedMeetup) |
| 2 | `src/app/domains/check-in/interfaces/index.ts` | Barrel export |
| 3 | `src/app/domains/check-in/services/check-in-sqlite/check-in-sqlite.service.ts` | SQLite persistence service mirroring TasksSqliteService |
| 4 | `src/app/domains/check-in/services/check-in-local-storage/check-in-local-storage.service.ts` | LocalStorage persistence service mirroring TasksLocalStorageService |
| 5 | `src/app/domains/check-in/services/check-in/check-in.service.ts` | Platform-routing service mirroring TasksService |
| 6 | `src/app/domains/check-in/services/index.ts` | Barrel export for services |
| 7 | `src/app/domains/check-in/services/check-in-sqlite/check-in-sqlite.service.spec.ts` | Unit tests for SQLite service |
| 8 | `src/app/domains/check-in/services/check-in-local-storage/check-in-local-storage.service.spec.ts` | Unit tests for localStorage service |
| 9 | `src/app/domains/check-in/services/check-in/check-in.service.spec.ts` | Unit tests for routing service |

### To Modify

None. This task only creates new files.

### To Leave Alone

- `src/app/domains/tasks/` -- Reference domain, read-only
- `src/app/core/` -- Core services are consumed, not modified
- `src/app/domains/check-in/pages/` -- Created in later tasks
- `src/app/domains/check-in/routes.ts` -- Created in later tasks
- `package.json` -- No new dependencies needed

---

## 6. Implementation Steps

### Step 1: Define domain interfaces

**Action**: Create the type definitions for the check-in domain. Use the same file structure as `domains/tasks/interfaces/task.ts` -- a single file with all interfaces, plus a barrel `index.ts`.

**File**: `src/app/domains/check-in/interfaces/check-in.ts`

**Pattern**:

```typescript
export type Partner = 'A' | 'B';

export interface CheckInSession {
  id: string;
  createdAt: string;
  partner: Partner;
  submitted: boolean;
  expiredAt: string | null;
}

export interface CheckInResponse {
  id: string;
  sessionId: string;
  questionIndex: number;
  score: number;
  answeredAt: string;
}

export interface QualityScore {
  communicationHonesty: number;
  mutualRespect: number;
  prioritization: number;
  longTermViability: number;
}

export interface CompletedMeetup {
  id: string;
  date: string;
  partnerA: { responses: CheckInResponse[]; qualities: QualityScore };
  partnerB: { responses: CheckInResponse[]; qualities: QualityScore };
}
```

**File**: `src/app/domains/check-in/interfaces/index.ts`

**Pattern**:

```typescript
export * from './check-in';
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 2: Implement CheckInSqliteService

**Action**: Create the SQLite persistence service. Mirror `TasksSqliteService` exactly: same class shape, same constructor injection of `SqliteService` and `PlatformService`, same `setUpgradeStatements()` call in constructor, same method return types. The only differences are the database name, table names, column names, and SQL statements.

**File**: `src/app/domains/check-in/services/check-in-sqlite/check-in-sqlite.service.ts`

**Pattern**:

```typescript
import { Injectable } from '@angular/core';
import { PlatformService, SqliteService } from '@app/core';
import { CheckInSession, CheckInResponse } from '../../interfaces';

@Injectable({
  providedIn: 'root',
})
export class CheckInSqliteService {
  private readonly database = 'check-in';
  private readonly sessionsTable = 'check_in_sessions';
  private readonly responsesTable = 'check_in_responses';

  constructor(
    private readonly sqliteService: SqliteService,
    private readonly platformService: PlatformService,
  ) {
    void this.setUpgradeStatements();
  }

  public async createSession(session: CheckInSession): Promise<void> {
    await this.sqliteService.run({
      database: this.database,
      statement: `INSERT INTO ${this.sessionsTable} (id, created_at, partner, submitted, expired_at) VALUES (?, ?, ?, ?, ?)`,
      values: [
        session.id,
        session.createdAt,
        session.partner,
        session.submitted ? 1 : 0,
        session.expiredAt,
      ],
    });
  }

  public async saveResponse(response: CheckInResponse): Promise<void> {
    await this.sqliteService.run({
      database: this.database,
      statement: `INSERT OR REPLACE INTO ${this.responsesTable} (id, session_id, question_index, score, answered_at) VALUES (?, ?, ?, ?, ?)`,
      values: [
        response.id,
        response.sessionId,
        response.questionIndex,
        response.score,
        response.answeredAt,
      ],
    });
  }

  public async selectSessionById(id: CheckInSession['id']): Promise<CheckInSession | null> {
    const result = await this.sqliteService.query({
      database: this.database,
      statement: `SELECT * FROM ${this.sessionsTable} WHERE id = ?`,
      values: [id],
    });
    if (result.values.length === 0) {
      return null;
    }
    return this.mapSessionRow(result.values[0]);
  }

  public async selectCompletedSessions(): Promise<CheckInSession[]> {
    const result = await this.sqliteService.query({
      database: this.database,
      statement: `SELECT * FROM ${this.sessionsTable} WHERE submitted = 1 ORDER BY created_at DESC`,
    });
    return result.values.map((row: any) => this.mapSessionRow(row));
  }

  public async selectResponsesBySessionId(sessionId: CheckInSession['id']): Promise<CheckInResponse[]> {
    const result = await this.sqliteService.query({
      database: this.database,
      statement: `SELECT * FROM ${this.responsesTable} WHERE session_id = ?`,
      values: [sessionId],
    });
    return result.values.map((row: any) => this.mapResponseRow(row));
  }

  public async updateSession(
    id: CheckInSession['id'],
    options: Omit<CheckInSession, 'id'>,
  ): Promise<void> {
    await this.sqliteService.run({
      database: this.database,
      statement: `UPDATE ${this.sessionsTable} SET created_at = ?, partner = ?, submitted = ?, expired_at = ? WHERE id = ?`,
      values: [
        options.createdAt,
        options.partner,
        options.submitted ? 1 : 0,
        options.expiredAt,
        id,
      ],
    });
  }

  public async deleteSession(id: CheckInSession['id']): Promise<void> {
    await this.sqliteService.run({
      database: this.database,
      statement: `DELETE FROM ${this.responsesTable} WHERE session_id = ?`,
      values: [id],
    });
    await this.sqliteService.run({
      database: this.database,
      statement: `DELETE FROM ${this.sessionsTable} WHERE id = ?`,
      values: [id],
    });
  }

  private mapSessionRow(row: any): CheckInSession {
    return {
      id: row.id,
      createdAt: row.created_at,
      partner: row.partner,
      submitted: row.submitted === 1,
      expiredAt: row.expired_at ?? null,
    };
  }

  private mapResponseRow(row: any): CheckInResponse {
    return {
      id: row.id,
      sessionId: row.session_id,
      questionIndex: row.question_index,
      score: row.score,
      answeredAt: row.answered_at,
    };
  }

  private async setUpgradeStatements(): Promise<void> {
    const isNative = this.platformService.isNative();
    if (!isNative) {
      return;
    }
    await this.sqliteService.addUpgradeStatement({
      database: this.database,
      upgrade: [
        {
          toVersion: 1,
          statements: [
            `CREATE TABLE IF NOT EXISTS ${this.sessionsTable} (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, partner TEXT NOT NULL CHECK(partner IN ('A', 'B')), submitted INTEGER NOT NULL DEFAULT 0, expired_at TEXT)`,
            `CREATE TABLE IF NOT EXISTS ${this.responsesTable} (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, question_index INTEGER NOT NULL CHECK(question_index BETWEEN 0 AND 9), score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 10), answered_at TEXT NOT NULL, FOREIGN KEY (session_id) REFERENCES ${this.sessionsTable}(id))`,
            `CREATE UNIQUE INDEX IF NOT EXISTS idx_responses_session_question ON ${this.responsesTable}(session_id, question_index)`,
          ],
        },
      ],
    });
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 3: Implement CheckInLocalStorageService

**Action**: Create the localStorage persistence service. Mirror `TasksLocalStorageService` exactly: same constructor injection of `CapacitorPreferencesService`, same JSON serialization pattern, same method signatures adapted for check-in data. Uses two separate keys for sessions and responses.

**File**: `src/app/domains/check-in/services/check-in-local-storage/check-in-local-storage.service.ts`

**Pattern**:

```typescript
import { Injectable } from '@angular/core';
import { CapacitorPreferencesService } from '@app/core';
import { CheckInSession, CheckInResponse } from '../../interfaces';

@Injectable({
  providedIn: 'root',
})
export class CheckInLocalStorageService {
  private readonly sessionsKey = 'check-in-sessions';
  private readonly responsesKey = 'check-in-responses';

  constructor(
    private readonly capacitorPreferencesService: CapacitorPreferencesService,
  ) {}

  public async createSession(session: CheckInSession): Promise<void> {
    const sessions = await this.selectAllSessions();
    sessions.push(session);
    await this.capacitorPreferencesService.set({
      key: this.sessionsKey,
      value: JSON.stringify(sessions),
    });
  }

  public async saveResponse(response: CheckInResponse): Promise<void> {
    const responses = await this.selectAllResponses();
    const existingIndex = responses.findIndex(
      r => r.sessionId === response.sessionId && r.questionIndex === response.questionIndex,
    );
    if (existingIndex !== -1) {
      responses[existingIndex] = response;
    } else {
      responses.push(response);
    }
    await this.capacitorPreferencesService.set({
      key: this.responsesKey,
      value: JSON.stringify(responses),
    });
  }

  public async selectSessionById(id: CheckInSession['id']): Promise<CheckInSession | null> {
    const sessions = await this.selectAllSessions();
    const found = sessions.find(s => s.id === id);
    return found || null;
  }

  public async selectCompletedSessions(): Promise<CheckInSession[]> {
    const sessions = await this.selectAllSessions();
    return sessions
      .filter(s => s.submitted)
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }

  public async selectResponsesBySessionId(sessionId: CheckInSession['id']): Promise<CheckInResponse[]> {
    const responses = await this.selectAllResponses();
    return responses.filter(r => r.sessionId === sessionId);
  }

  public async updateSession(
    id: CheckInSession['id'],
    options: Omit<CheckInSession, 'id'>,
  ): Promise<void> {
    const sessions = await this.selectAllSessions();
    const foundIndex = sessions.findIndex(s => s.id === id);
    if (foundIndex === -1) {
      return;
    }
    sessions[foundIndex] = {
      ...sessions[foundIndex],
      ...options,
    };
    await this.capacitorPreferencesService.set({
      key: this.sessionsKey,
      value: JSON.stringify(sessions),
    });
  }

  public async deleteSession(id: CheckInSession['id']): Promise<void> {
    const sessions = await this.selectAllSessions();
    const newSessions = sessions.filter(s => s.id !== id);
    await this.capacitorPreferencesService.set({
      key: this.sessionsKey,
      value: JSON.stringify(newSessions),
    });

    const responses = await this.selectAllResponses();
    const newResponses = responses.filter(r => r.sessionId !== id);
    await this.capacitorPreferencesService.set({
      key: this.responsesKey,
      value: JSON.stringify(newResponses),
    });
  }

  private async selectAllSessions(): Promise<CheckInSession[]> {
    const result = await this.capacitorPreferencesService.get({
      key: this.sessionsKey,
    });
    return result.value ? JSON.parse(result.value) : [];
  }

  private async selectAllResponses(): Promise<CheckInResponse[]> {
    const result = await this.capacitorPreferencesService.get({
      key: this.responsesKey,
    });
    return result.value ? JSON.parse(result.value) : [];
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 4: Implement CheckInService (platform routing)

**Action**: Create the platform-routing service. Mirror `TasksService` exactly: same constructor injection of both backend services, same `Capacitor.getPlatform() === 'web'` check in every method, same `nanoid()` for ID generation. This is the public API that page services will consume.

**File**: `src/app/domains/check-in/services/check-in/check-in.service.ts`

**Pattern**:

```typescript
import { Injectable } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { nanoid } from 'nanoid';
import { CheckInSession, CheckInResponse } from '../../interfaces';
import { CheckInLocalStorageService } from '../check-in-local-storage/check-in-local-storage.service';
import { CheckInSqliteService } from '../check-in-sqlite/check-in-sqlite.service';

@Injectable({
  providedIn: 'root',
})
export class CheckInService {
  constructor(
    private readonly checkInSqliteService: CheckInSqliteService,
    private readonly checkInLocalStorageService: CheckInLocalStorageService,
  ) {}

  public async createSession(options: Omit<CheckInSession, 'id'>): Promise<string> {
    const id = nanoid();
    const session: CheckInSession = {
      ...options,
      id,
    };
    const isWeb = Capacitor.getPlatform() === 'web';
    if (isWeb) {
      await this.checkInLocalStorageService.createSession(session);
    } else {
      await this.checkInSqliteService.createSession(session);
    }
    return id;
  }

  public async saveResponse(options: Omit<CheckInResponse, 'id'>): Promise<void> {
    const response: CheckInResponse = {
      ...options,
      id: nanoid(),
    };
    const isWeb = Capacitor.getPlatform() === 'web';
    if (isWeb) {
      await this.checkInLocalStorageService.saveResponse(response);
    } else {
      await this.checkInSqliteService.saveResponse(response);
    }
  }

  public getSessionById(id: CheckInSession['id']): Promise<CheckInSession | null> {
    const isWeb = Capacitor.getPlatform() === 'web';
    if (isWeb) {
      return this.checkInLocalStorageService.selectSessionById(id);
    } else {
      return this.checkInSqliteService.selectSessionById(id);
    }
  }

  public getCompletedSessions(): Promise<CheckInSession[]> {
    const isWeb = Capacitor.getPlatform() === 'web';
    if (isWeb) {
      return this.checkInLocalStorageService.selectCompletedSessions();
    } else {
      return this.checkInSqliteService.selectCompletedSessions();
    }
  }

  public getResponsesBySessionId(sessionId: CheckInSession['id']): Promise<CheckInResponse[]> {
    const isWeb = Capacitor.getPlatform() === 'web';
    if (isWeb) {
      return this.checkInLocalStorageService.selectResponsesBySessionId(sessionId);
    } else {
      return this.checkInSqliteService.selectResponsesBySessionId(sessionId);
    }
  }

  public async updateSession(
    id: CheckInSession['id'],
    options: Omit<CheckInSession, 'id'>,
  ): Promise<void> {
    const isWeb = Capacitor.getPlatform() === 'web';
    if (isWeb) {
      await this.checkInLocalStorageService.updateSession(id, options);
    } else {
      await this.checkInSqliteService.updateSession(id, options);
    }
  }

  public async deleteSession(id: CheckInSession['id']): Promise<void> {
    const isWeb = Capacitor.getPlatform() === 'web';
    if (isWeb) {
      await this.checkInLocalStorageService.deleteSession(id);
    } else {
      await this.checkInSqliteService.deleteSession(id);
    }
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 5: Create barrel exports

**Action**: Create the barrel export for services. Mirror `domains/tasks/services/index.ts`.

**File**: `src/app/domains/check-in/services/index.ts`

**Pattern**:

```typescript
export * from './check-in-local-storage/check-in-local-storage.service';
export * from './check-in-sqlite/check-in-sqlite.service';
export * from './check-in/check-in.service';
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

## 7. Tests

### Test 1: `check-in-sqlite.service.spec.ts`

**File**: `src/app/domains/check-in/services/check-in-sqlite/check-in-sqlite.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { PlatformService, SqliteService } from '@app/core';
import { CheckInSqliteService } from './check-in-sqlite.service';
import { CheckInSession, CheckInResponse } from '../../interfaces';

describe('CheckInSqliteService', () => {
  let service: CheckInSqliteService;
  let sqliteSpy: jasmine.SpyObj<SqliteService>;
  let platformSpy: jasmine.SpyObj<PlatformService>;

  function fakeSession(overrides: Partial<CheckInSession> = {}): CheckInSession {
    return {
      id: 'sess-1',
      createdAt: '2026-04-20T10:00:00.000Z',
      partner: 'A',
      submitted: false,
      expiredAt: null,
      ...overrides,
    };
  }

  function fakeResponse(overrides: Partial<CheckInResponse> = {}): CheckInResponse {
    return {
      id: 'resp-1',
      sessionId: 'sess-1',
      questionIndex: 0,
      score: 7,
      answeredAt: '2026-04-20T10:01:00.000Z',
      ...overrides,
    };
  }

  beforeEach(() => {
    sqliteSpy = jasmine.createSpyObj('SqliteService', [
      'addUpgradeStatement',
      'run',
      'query',
    ]);
    sqliteSpy.addUpgradeStatement.and.resolveTo();
    sqliteSpy.run.and.resolveTo();
    sqliteSpy.query.and.resolveTo({ values: [] });

    platformSpy = jasmine.createSpyObj('PlatformService', ['isNative']);
    platformSpy.isNative.and.returnValue(true);

    TestBed.configureTestingModule({
      providers: [
        CheckInSqliteService,
        { provide: SqliteService, useValue: sqliteSpy },
        { provide: PlatformService, useValue: platformSpy },
      ],
    });
    service = TestBed.inject(CheckInSqliteService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should register upgrade statements on native', () => {
    expect(sqliteSpy.addUpgradeStatement).toHaveBeenCalledWith(
      jasmine.objectContaining({
        database: 'check-in',
        upgrade: jasmine.arrayContaining([
          jasmine.objectContaining({ toVersion: 1 }),
        ]),
      }),
    );
  });

  it('should not register upgrade statements on web', () => {
    sqliteSpy.addUpgradeStatement.calls.reset();
    platformSpy.isNative.and.returnValue(false);

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        CheckInSqliteService,
        { provide: SqliteService, useValue: sqliteSpy },
        { provide: PlatformService, useValue: platformSpy },
      ],
    });
    TestBed.inject(CheckInSqliteService);

    expect(sqliteSpy.addUpgradeStatement).not.toHaveBeenCalled();
  });

  it('createSession should insert a row into check_in_sessions', async () => {
    const session = fakeSession();

    await service.createSession(session);

    expect(sqliteSpy.run).toHaveBeenCalledWith(
      jasmine.objectContaining({
        database: 'check-in',
        statement: jasmine.stringContaining('INSERT INTO check_in_sessions'),
        values: ['sess-1', '2026-04-20T10:00:00.000Z', 'A', 0, null],
      }),
    );
  });

  it('createSession should convert submitted boolean to integer', async () => {
    const session = fakeSession({ submitted: true });

    await service.createSession(session);

    expect(sqliteSpy.run).toHaveBeenCalledWith(
      jasmine.objectContaining({
        values: jasmine.arrayContaining([1]),
      }),
    );
  });

  it('saveResponse should insert or replace a row into check_in_responses', async () => {
    const response = fakeResponse();

    await service.saveResponse(response);

    expect(sqliteSpy.run).toHaveBeenCalledWith(
      jasmine.objectContaining({
        database: 'check-in',
        statement: jasmine.stringContaining('INSERT OR REPLACE INTO check_in_responses'),
        values: ['resp-1', 'sess-1', 0, 7, '2026-04-20T10:01:00.000Z'],
      }),
    );
  });

  it('selectSessionById should return a mapped session when found', async () => {
    sqliteSpy.query.and.resolveTo({
      values: [{
        id: 'sess-1',
        created_at: '2026-04-20T10:00:00.000Z',
        partner: 'A',
        submitted: 0,
        expired_at: null,
      }],
    });

    const result = await service.selectSessionById('sess-1');

    expect(result).toEqual({
      id: 'sess-1',
      createdAt: '2026-04-20T10:00:00.000Z',
      partner: 'A',
      submitted: false,
      expiredAt: null,
    });
  });

  it('selectSessionById should return null when not found', async () => {
    sqliteSpy.query.and.resolveTo({ values: [] });

    const result = await service.selectSessionById('no-such-id');

    expect(result).toBeNull();
  });

  it('selectCompletedSessions should query for submitted sessions ordered by date', async () => {
    sqliteSpy.query.and.resolveTo({
      values: [
        { id: 's1', created_at: '2026-04-20T10:00:00.000Z', partner: 'A', submitted: 1, expired_at: null },
        { id: 's2', created_at: '2026-04-19T10:00:00.000Z', partner: 'B', submitted: 1, expired_at: null },
      ],
    });

    const result = await service.selectCompletedSessions();

    expect(result.length).toBe(2);
    expect(result[0].id).toBe('s1');
    expect(result[0].submitted).toBeTrue();
    expect(sqliteSpy.query).toHaveBeenCalledWith(
      jasmine.objectContaining({
        database: 'check-in',
        statement: jasmine.stringContaining('submitted = 1'),
      }),
    );
  });

  it('selectResponsesBySessionId should return mapped responses', async () => {
    sqliteSpy.query.and.resolveTo({
      values: [
        { id: 'r1', session_id: 'sess-1', question_index: 0, score: 7, answered_at: '2026-04-20T10:01:00.000Z' },
        { id: 'r2', session_id: 'sess-1', question_index: 1, score: 8, answered_at: '2026-04-20T10:02:00.000Z' },
      ],
    });

    const result = await service.selectResponsesBySessionId('sess-1');

    expect(result.length).toBe(2);
    expect(result[0]).toEqual({
      id: 'r1',
      sessionId: 'sess-1',
      questionIndex: 0,
      score: 7,
      answeredAt: '2026-04-20T10:01:00.000Z',
    });
  });

  it('updateSession should update the session row', async () => {
    const options: Omit<CheckInSession, 'id'> = {
      createdAt: '2026-04-20T10:00:00.000Z',
      partner: 'A',
      submitted: true,
      expiredAt: null,
    };

    await service.updateSession('sess-1', options);

    expect(sqliteSpy.run).toHaveBeenCalledWith(
      jasmine.objectContaining({
        database: 'check-in',
        statement: jasmine.stringContaining('UPDATE check_in_sessions'),
        values: ['2026-04-20T10:00:00.000Z', 'A', 1, null, 'sess-1'],
      }),
    );
  });

  it('deleteSession should delete responses first then session', async () => {
    await service.deleteSession('sess-1');

    const calls = sqliteSpy.run.calls.allArgs();
    expect(calls.length).toBe(2);
    expect((calls[0][0] as any).statement).toContain('DELETE FROM check_in_responses');
    expect((calls[0][0] as any).values).toEqual(['sess-1']);
    expect((calls[1][0] as any).statement).toContain('DELETE FROM check_in_sessions');
    expect((calls[1][0] as any).values).toEqual(['sess-1']);
  });
});
```

### Test 2: `check-in-local-storage.service.spec.ts`

**File**: `src/app/domains/check-in/services/check-in-local-storage/check-in-local-storage.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { CapacitorPreferencesService } from '@app/core';
import { CheckInLocalStorageService } from './check-in-local-storage.service';
import { CheckInSession, CheckInResponse } from '../../interfaces';

describe('CheckInLocalStorageService', () => {
  let service: CheckInLocalStorageService;
  let preferencesSpy: jasmine.SpyObj<CapacitorPreferencesService>;

  let sessionsStore: string | null;
  let responsesStore: string | null;

  function fakeSession(overrides: Partial<CheckInSession> = {}): CheckInSession {
    return {
      id: 'sess-1',
      createdAt: '2026-04-20T10:00:00.000Z',
      partner: 'A',
      submitted: false,
      expiredAt: null,
      ...overrides,
    };
  }

  function fakeResponse(overrides: Partial<CheckInResponse> = {}): CheckInResponse {
    return {
      id: 'resp-1',
      sessionId: 'sess-1',
      questionIndex: 0,
      score: 7,
      answeredAt: '2026-04-20T10:01:00.000Z',
      ...overrides,
    };
  }

  beforeEach(() => {
    sessionsStore = null;
    responsesStore = null;

    preferencesSpy = jasmine.createSpyObj('CapacitorPreferencesService', [
      'get',
      'set',
    ]);
    preferencesSpy.get.and.callFake((options: { key: string }) => {
      if (options.key === 'check-in-sessions') {
        return Promise.resolve({ value: sessionsStore });
      }
      if (options.key === 'check-in-responses') {
        return Promise.resolve({ value: responsesStore });
      }
      return Promise.resolve({ value: null });
    });
    preferencesSpy.set.and.callFake((options: { key: string; value: string }) => {
      if (options.key === 'check-in-sessions') {
        sessionsStore = options.value;
      }
      if (options.key === 'check-in-responses') {
        responsesStore = options.value;
      }
      return Promise.resolve();
    });

    TestBed.configureTestingModule({
      providers: [
        CheckInLocalStorageService,
        { provide: CapacitorPreferencesService, useValue: preferencesSpy },
      ],
    });
    service = TestBed.inject(CheckInLocalStorageService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('createSession should store the session', async () => {
    const session = fakeSession();

    await service.createSession(session);

    const stored = JSON.parse(sessionsStore!);
    expect(stored.length).toBe(1);
    expect(stored[0].id).toBe('sess-1');
  });

  it('createSession should append to existing sessions', async () => {
    sessionsStore = JSON.stringify([fakeSession({ id: 'existing' })]);

    await service.createSession(fakeSession({ id: 'new' }));

    const stored = JSON.parse(sessionsStore!);
    expect(stored.length).toBe(2);
  });

  it('saveResponse should store the response', async () => {
    const response = fakeResponse();

    await service.saveResponse(response);

    const stored = JSON.parse(responsesStore!);
    expect(stored.length).toBe(1);
    expect(stored[0].id).toBe('resp-1');
  });

  it('saveResponse should upsert when same sessionId and questionIndex exist', async () => {
    responsesStore = JSON.stringify([fakeResponse({ id: 'old', score: 5 })]);

    await service.saveResponse(fakeResponse({ id: 'new', score: 9 }));

    const stored = JSON.parse(responsesStore!);
    expect(stored.length).toBe(1);
    expect(stored[0].id).toBe('new');
    expect(stored[0].score).toBe(9);
  });

  it('saveResponse should append when different questionIndex', async () => {
    responsesStore = JSON.stringify([fakeResponse({ questionIndex: 0 })]);

    await service.saveResponse(fakeResponse({ id: 'resp-2', questionIndex: 1 }));

    const stored = JSON.parse(responsesStore!);
    expect(stored.length).toBe(2);
  });

  it('selectSessionById should return session when found', async () => {
    sessionsStore = JSON.stringify([fakeSession()]);

    const result = await service.selectSessionById('sess-1');

    expect(result).toEqual(fakeSession());
  });

  it('selectSessionById should return null when not found', async () => {
    sessionsStore = JSON.stringify([fakeSession()]);

    const result = await service.selectSessionById('no-such-id');

    expect(result).toBeNull();
  });

  it('selectCompletedSessions should return only submitted sessions', async () => {
    sessionsStore = JSON.stringify([
      fakeSession({ id: 's1', submitted: true }),
      fakeSession({ id: 's2', submitted: false }),
      fakeSession({ id: 's3', submitted: true }),
    ]);

    const result = await service.selectCompletedSessions();

    expect(result.length).toBe(2);
    expect(result.every(s => s.submitted)).toBeTrue();
  });

  it('selectCompletedSessions should sort by createdAt descending', async () => {
    sessionsStore = JSON.stringify([
      fakeSession({ id: 's1', submitted: true, createdAt: '2026-04-18T10:00:00.000Z' }),
      fakeSession({ id: 's2', submitted: true, createdAt: '2026-04-20T10:00:00.000Z' }),
    ]);

    const result = await service.selectCompletedSessions();

    expect(result[0].id).toBe('s2');
    expect(result[1].id).toBe('s1');
  });

  it('selectResponsesBySessionId should filter by sessionId', async () => {
    responsesStore = JSON.stringify([
      fakeResponse({ id: 'r1', sessionId: 'sess-1' }),
      fakeResponse({ id: 'r2', sessionId: 'sess-2' }),
      fakeResponse({ id: 'r3', sessionId: 'sess-1' }),
    ]);

    const result = await service.selectResponsesBySessionId('sess-1');

    expect(result.length).toBe(2);
    expect(result.every(r => r.sessionId === 'sess-1')).toBeTrue();
  });

  it('updateSession should update the matching session', async () => {
    sessionsStore = JSON.stringify([fakeSession()]);

    await service.updateSession('sess-1', {
      createdAt: '2026-04-20T10:00:00.000Z',
      partner: 'A',
      submitted: true,
      expiredAt: null,
    });

    const stored = JSON.parse(sessionsStore!);
    expect(stored[0].submitted).toBeTrue();
  });

  it('updateSession should no-op when session not found', async () => {
    sessionsStore = JSON.stringify([fakeSession()]);
    const before = sessionsStore;

    await service.updateSession('no-such-id', {
      createdAt: '2026-04-20T10:00:00.000Z',
      partner: 'A',
      submitted: true,
      expiredAt: null,
    });

    expect(sessionsStore).toBe(before);
  });

  it('deleteSession should remove the session and its responses', async () => {
    sessionsStore = JSON.stringify([
      fakeSession({ id: 'sess-1' }),
      fakeSession({ id: 'sess-2' }),
    ]);
    responsesStore = JSON.stringify([
      fakeResponse({ id: 'r1', sessionId: 'sess-1' }),
      fakeResponse({ id: 'r2', sessionId: 'sess-2' }),
      fakeResponse({ id: 'r3', sessionId: 'sess-1' }),
    ]);

    await service.deleteSession('sess-1');

    const storedSessions = JSON.parse(sessionsStore!);
    expect(storedSessions.length).toBe(1);
    expect(storedSessions[0].id).toBe('sess-2');

    const storedResponses = JSON.parse(responsesStore!);
    expect(storedResponses.length).toBe(1);
    expect(storedResponses[0].id).toBe('r2');
  });

  it('selectSessionById should return null when store is empty', async () => {
    const result = await service.selectSessionById('any-id');

    expect(result).toBeNull();
  });

  it('selectCompletedSessions should return empty when store is empty', async () => {
    const result = await service.selectCompletedSessions();

    expect(result).toEqual([]);
  });

  it('selectResponsesBySessionId should return empty when store is empty', async () => {
    const result = await service.selectResponsesBySessionId('any-id');

    expect(result).toEqual([]);
  });
});
```

### Test 3: `check-in.service.spec.ts`

**File**: `src/app/domains/check-in/services/check-in/check-in.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { Capacitor } from '@capacitor/core';
import { CheckInService } from './check-in.service';
import { CheckInSqliteService } from '../check-in-sqlite/check-in-sqlite.service';
import { CheckInLocalStorageService } from '../check-in-local-storage/check-in-local-storage.service';
import { CheckInSession, CheckInResponse } from '../../interfaces';

describe('CheckInService', () => {
  let service: CheckInService;
  let sqliteSpy: jasmine.SpyObj<CheckInSqliteService>;
  let localStorageSpy: jasmine.SpyObj<CheckInLocalStorageService>;

  const sessionOptions: Omit<CheckInSession, 'id'> = {
    createdAt: '2026-04-20T10:00:00.000Z',
    partner: 'A',
    submitted: false,
    expiredAt: null,
  };

  const responseOptions: Omit<CheckInResponse, 'id'> = {
    sessionId: 'sess-1',
    questionIndex: 0,
    score: 7,
    answeredAt: '2026-04-20T10:01:00.000Z',
  };

  function fakeSession(overrides: Partial<CheckInSession> = {}): CheckInSession {
    return {
      id: 'sess-1',
      createdAt: '2026-04-20T10:00:00.000Z',
      partner: 'A',
      submitted: false,
      expiredAt: null,
      ...overrides,
    };
  }

  beforeEach(() => {
    sqliteSpy = jasmine.createSpyObj('CheckInSqliteService', [
      'createSession',
      'saveResponse',
      'selectSessionById',
      'selectCompletedSessions',
      'selectResponsesBySessionId',
      'updateSession',
      'deleteSession',
    ]);
    sqliteSpy.createSession.and.resolveTo();
    sqliteSpy.saveResponse.and.resolveTo();
    sqliteSpy.selectSessionById.and.resolveTo(null);
    sqliteSpy.selectCompletedSessions.and.resolveTo([]);
    sqliteSpy.selectResponsesBySessionId.and.resolveTo([]);
    sqliteSpy.updateSession.and.resolveTo();
    sqliteSpy.deleteSession.and.resolveTo();

    localStorageSpy = jasmine.createSpyObj('CheckInLocalStorageService', [
      'createSession',
      'saveResponse',
      'selectSessionById',
      'selectCompletedSessions',
      'selectResponsesBySessionId',
      'updateSession',
      'deleteSession',
    ]);
    localStorageSpy.createSession.and.resolveTo();
    localStorageSpy.saveResponse.and.resolveTo();
    localStorageSpy.selectSessionById.and.resolveTo(null);
    localStorageSpy.selectCompletedSessions.and.resolveTo([]);
    localStorageSpy.selectResponsesBySessionId.and.resolveTo([]);
    localStorageSpy.updateSession.and.resolveTo();
    localStorageSpy.deleteSession.and.resolveTo();

    TestBed.configureTestingModule({
      providers: [
        CheckInService,
        { provide: CheckInSqliteService, useValue: sqliteSpy },
        { provide: CheckInLocalStorageService, useValue: localStorageSpy },
      ],
    });
    service = TestBed.inject(CheckInService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('on web platform', () => {
    beforeEach(() => {
      spyOn(Capacitor, 'getPlatform').and.returnValue('web');
    });

    it('createSession should delegate to localStorage service', async () => {
      const id = await service.createSession(sessionOptions);

      expect(id).toBeTruthy();
      expect(localStorageSpy.createSession).toHaveBeenCalledWith(
        jasmine.objectContaining({
          id,
          partner: 'A',
          submitted: false,
        }),
      );
      expect(sqliteSpy.createSession).not.toHaveBeenCalled();
    });

    it('createSession should generate a unique id', async () => {
      const id1 = await service.createSession(sessionOptions);
      const id2 = await service.createSession(sessionOptions);

      expect(id1).not.toBe(id2);
    });

    it('saveResponse should delegate to localStorage service', async () => {
      await service.saveResponse(responseOptions);

      expect(localStorageSpy.saveResponse).toHaveBeenCalledWith(
        jasmine.objectContaining({
          sessionId: 'sess-1',
          questionIndex: 0,
          score: 7,
        }),
      );
      expect(sqliteSpy.saveResponse).not.toHaveBeenCalled();
    });

    it('getSessionById should delegate to localStorage service', async () => {
      localStorageSpy.selectSessionById.and.resolveTo(fakeSession());

      const result = await service.getSessionById('sess-1');

      expect(result).toEqual(fakeSession());
      expect(localStorageSpy.selectSessionById).toHaveBeenCalledWith('sess-1');
      expect(sqliteSpy.selectSessionById).not.toHaveBeenCalled();
    });

    it('getCompletedSessions should delegate to localStorage service', async () => {
      localStorageSpy.selectCompletedSessions.and.resolveTo([fakeSession({ submitted: true })]);

      const result = await service.getCompletedSessions();

      expect(result.length).toBe(1);
      expect(localStorageSpy.selectCompletedSessions).toHaveBeenCalled();
      expect(sqliteSpy.selectCompletedSessions).not.toHaveBeenCalled();
    });

    it('getResponsesBySessionId should delegate to localStorage service', async () => {
      await service.getResponsesBySessionId('sess-1');

      expect(localStorageSpy.selectResponsesBySessionId).toHaveBeenCalledWith('sess-1');
      expect(sqliteSpy.selectResponsesBySessionId).not.toHaveBeenCalled();
    });

    it('updateSession should delegate to localStorage service', async () => {
      await service.updateSession('sess-1', sessionOptions);

      expect(localStorageSpy.updateSession).toHaveBeenCalledWith('sess-1', sessionOptions);
      expect(sqliteSpy.updateSession).not.toHaveBeenCalled();
    });

    it('deleteSession should delegate to localStorage service', async () => {
      await service.deleteSession('sess-1');

      expect(localStorageSpy.deleteSession).toHaveBeenCalledWith('sess-1');
      expect(sqliteSpy.deleteSession).not.toHaveBeenCalled();
    });
  });

  describe('on native platform', () => {
    beforeEach(() => {
      spyOn(Capacitor, 'getPlatform').and.returnValue('ios');
    });

    it('createSession should delegate to sqlite service', async () => {
      const id = await service.createSession(sessionOptions);

      expect(id).toBeTruthy();
      expect(sqliteSpy.createSession).toHaveBeenCalledWith(
        jasmine.objectContaining({
          id,
          partner: 'A',
          submitted: false,
        }),
      );
      expect(localStorageSpy.createSession).not.toHaveBeenCalled();
    });

    it('saveResponse should delegate to sqlite service', async () => {
      await service.saveResponse(responseOptions);

      expect(sqliteSpy.saveResponse).toHaveBeenCalledWith(
        jasmine.objectContaining({
          sessionId: 'sess-1',
          questionIndex: 0,
          score: 7,
        }),
      );
      expect(localStorageSpy.saveResponse).not.toHaveBeenCalled();
    });

    it('getSessionById should delegate to sqlite service', async () => {
      await service.getSessionById('sess-1');

      expect(sqliteSpy.selectSessionById).toHaveBeenCalledWith('sess-1');
      expect(localStorageSpy.selectSessionById).not.toHaveBeenCalled();
    });

    it('getCompletedSessions should delegate to sqlite service', async () => {
      await service.getCompletedSessions();

      expect(sqliteSpy.selectCompletedSessions).toHaveBeenCalled();
      expect(localStorageSpy.selectCompletedSessions).not.toHaveBeenCalled();
    });

    it('getResponsesBySessionId should delegate to sqlite service', async () => {
      await service.getResponsesBySessionId('sess-1');

      expect(sqliteSpy.selectResponsesBySessionId).toHaveBeenCalledWith('sess-1');
      expect(localStorageSpy.selectResponsesBySessionId).not.toHaveBeenCalled();
    });

    it('updateSession should delegate to sqlite service', async () => {
      await service.updateSession('sess-1', sessionOptions);

      expect(sqliteSpy.updateSession).toHaveBeenCalledWith('sess-1', sessionOptions);
      expect(localStorageSpy.updateSession).not.toHaveBeenCalled();
    });

    it('deleteSession should delegate to sqlite service', async () => {
      await service.deleteSession('sess-1');

      expect(sqliteSpy.deleteSession).toHaveBeenCalledWith('sess-1');
      expect(localStorageSpy.deleteSession).not.toHaveBeenCalled();
    });
  });
});
```

---

## 8. Commit Plan

| # | Message | Files |
|---|---------|-------|
| 1 | `feat(check-in): add domain interfaces for sessions and responses` | `interfaces/check-in.ts`, `interfaces/index.ts` |
| 2 | `feat(check-in): add SQLite persistence service with upgrade statements` | `services/check-in-sqlite/check-in-sqlite.service.ts`, `services/check-in-sqlite/check-in-sqlite.service.spec.ts` |
| 3 | `feat(check-in): add localStorage persistence service` | `services/check-in-local-storage/check-in-local-storage.service.ts`, `services/check-in-local-storage/check-in-local-storage.service.spec.ts` |
| 4 | `feat(check-in): add platform-routing service with nanoid IDs` | `services/check-in/check-in.service.ts`, `services/check-in/check-in.service.spec.ts`, `services/index.ts` |

---

## 9. Verification

After all steps are complete, run from `/projects/ionstarter/`:

```bash
# 1. TypeScript compilation
npx tsc --noEmit
# Expected: 0 errors

# 2. Full build
npm run build
# Expected: Build succeeds

# 3. Lint
npm run lint
# Expected: 0 errors, 0 warnings

# 4. Unit tests
npm run test:ci
# Expected: All tests pass, including:
#   - CheckInSqliteService: 11 specs
#   - CheckInLocalStorageService: 14 specs
#   - CheckInService: 15 specs

# 5. Verify file structure matches tasks domain pattern
ls -la src/app/domains/check-in/interfaces/
# Expected: check-in.ts, index.ts
ls -la src/app/domains/check-in/services/check-in-sqlite/
# Expected: check-in-sqlite.service.ts, check-in-sqlite.service.spec.ts
ls -la src/app/domains/check-in/services/check-in-local-storage/
# Expected: check-in-local-storage.service.ts, check-in-local-storage.service.spec.ts
ls -la src/app/domains/check-in/services/check-in/
# Expected: check-in.service.ts, check-in.service.spec.ts
ls -la src/app/domains/check-in/services/
# Expected: index.ts + the three service directories above
```

---

## 10. Rollback

All changes are new files in `src/app/domains/check-in/`. No existing files are modified. To revert:

```bash
# Option 1: Git revert all commits (if pushed)
git log --oneline -4  # find the 4 commit SHAs
git revert <sha4> <sha3> <sha2> <sha1>

# Option 2: Hard reset (if not pushed)
git reset --hard HEAD~4

# Option 3: Simple delete (since no existing files were modified)
rm -rf src/app/domains/check-in/
```

---

## 11. Deviations Allowed

| Area | Allowed Deviation |
|------|-------------------|
| **Column naming in SQLite** | Executor may use camelCase column names (matching the TypeScript interfaces) instead of snake_case. If camelCase is used, the `mapSessionRow`/`mapResponseRow` helpers become identity functions. The architecture doc shows snake_case, which is standard SQL convention. |
| **`expiredAt` type** | Executor may use `string \| undefined` instead of `string \| null` if preferred. The architecture doc shows optional (`expiredAt?`). The guide uses `string \| null` to match SQLite's null semantics. Either is acceptable. |
| **Additional CRUD methods** | Executor may add methods beyond the spec (e.g., `selectActiveSessions`, `selectSessionsByPartner`) if they see the need from later tasks. Must still have matching signatures across all three services. |
| **Upgrade statement format** | Executor may split the three SQL statements (two CREATE TABLE + one CREATE INDEX) into separate upgrade versions (v1, v2, v3) instead of a single v1 with three statements. Single v1 with all three is simpler and preferred. |
| **Test count** | Executor may add more tests. Must not remove any prescribed test cases. |
| **`INSERT OR REPLACE` vs separate check** | For `saveResponse` in the SQLite service, the guide uses `INSERT OR REPLACE`. Executor may use `INSERT ... ON CONFLICT DO UPDATE` instead. Both achieve upsert semantics via the unique index. |

---

## 12. Out of Scope

- **Routes, pages, or UI components** -- Created in Tasks 2-8, not this task
- **TanStack Query page services** -- Created in Task 2+; this task only creates the raw persistence layer
- **Quality score computation** -- Task 6; interfaces are defined here but computation logic is not
- **Draft auto-save logic** -- Task 4; the `saveResponse` upsert enables it, but the auto-save flow is Task 4's concern
- **Session expiry logic** -- Task 4; the `expiredAt` field and `updateSession` enable it, but the expiry scan is Task 4
- **Mock data file** -- Architecture mentions `check-in.mock.ts`; create it only if needed for tests. The persistence services can be fully tested with inline test data.
- **Modifying `src/app/core/`** -- Core services (`SqliteService`, `PlatformService`, `CapacitorPreferencesService`) are consumed as-is
- **Modifying `package.json`** -- All dependencies (`nanoid`, `@capacitor-community/sqlite`, `@capacitor/preferences`) are already installed
- **Tabs routing or navigation** -- Wired in later tasks
- **i18n translation keys** -- Added when UI components are built
- **Cross-domain imports** -- The check-in domain must not import from the tasks domain. It only imports from `@app/core`.
