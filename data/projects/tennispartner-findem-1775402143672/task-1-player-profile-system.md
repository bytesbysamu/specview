# 🛠️ Task 1: Player Profile System

**Purpose**: Create the foundational user profile structure that captures tennis-specific attributes needed for intelligent partner matching.

**Effort**: 3 days

**Dependencies**: None — this is the foundation

**Parallel With**: —

**Blocks**: Task 2 (Discovery/Matching), Task 3 (Connection/Messaging)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- User profile data model with tennis-specific fields
- Profile creation/edit API endpoints
- Profile creation UI flow (mobile-first)
- Basic validation and persistence
- Home court location capture with map integration

### What's NOT Included
- Match algorithm logic — belongs in Task 2 (Discovery)
- Messaging features — belongs in Task 3 (Connection)
- Profile photo upload — defer to post-MVP
- Social connections/friends list — unnecessary complexity for MVP

---

## Prerequisites

Before starting:
- Development environment configured (see [Architecture](./architecture.md) for stack)
- Database provisioned and accessible
- Authentication system in place (or stub it for now)
- Map/geocoding API key obtained (Google Maps or Mapbox)

---

## Implementation Steps

### Step 1: Define Profile Data Model

**File**: `src/models/player-profile.ts` (or equivalent)

**Purpose**: Establish the core data structure that all other features will reference

The profile model should be minimal but complete. Resist the urge to add "nice to have" fields—each field must serve the matching algorithm or improve user experience directly.

**Pattern**:
```typescript
interface PlayerProfile {
  id: string;
  userId: string;
  
  // Tennis-specific (required for matching)
  skillLevel: 'beginner' | 'intermediate' | 'advanced' | 'competitive';
  playStyle: 'singles' | 'doubles' | 'both';
  
  // Location (required for proximity matching)
  homeCourtLocation: {
    name: string;        // "Riverside Tennis Club"
    lat: number;
    lng: number;
  };
  
  // Availability (structured for overlap detection)
  availability: {
    dayOfWeek: number;   // 0-6 (Sunday-Saturday)
    startHour: number;   // 0-23
    endHour: number;     // 0-23
  }[];
  
  // Display
  displayName: string;
  bio?: string;          // Optional, max 200 chars
  
  // Metadata
  createdAt: Date;
  updatedAt: Date;
}
```

**Key decisions**:
- `skillLevel` uses self-assessment (simple, works for MVP)
- `availability` is an array of windows, not a complex calendar
- `homeCourtLocation` stores coordinates for distance calculations

---

### Step 2: Create Database Schema

**File**: `migrations/001_player_profiles.sql` (or ORM equivalent)

**Purpose**: Persist profiles with proper indexing for location queries

**Pattern**:
```sql
CREATE TABLE player_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  
  skill_level VARCHAR(20) NOT NULL,
  play_style VARCHAR(20) NOT NULL,
  
  home_court_name VARCHAR(200) NOT NULL,
  home_court_lat DECIMAL(10, 8) NOT NULL,
  home_court_lng DECIMAL(11, 8) NOT NULL,
  
  display_name VARCHAR(100) NOT NULL,
  bio VARCHAR(200),
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT valid_skill CHECK (skill_level IN ('beginner', 'intermediate', 'advanced', 'competitive')),
  CONSTRAINT valid_style CHECK (play_style IN ('singles', 'doubles', 'both'))
);

-- Spatial index for proximity searches (Task 2 will use this)
CREATE INDEX idx_profiles_location ON player_profiles 
  USING gist (ll_to_earth(home_court_lat, home_court_lng));

-- Availability as separate table for flexible querying
CREATE TABLE profile_availability (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id UUID NOT NULL REFERENCES player_profiles(id) ON DELETE CASCADE,
  day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
  start_hour SMALLINT NOT NULL CHECK (start_hour BETWEEN 0 AND 23),
  end_hour SMALLINT NOT NULL CHECK (end_hour BETWEEN 0 AND 23)
);
```

---

### Step 3: Build Profile API Endpoints

**File**: `src/api/profiles.ts`

**Purpose**: CRUD operations for profiles with proper validation

Following [Architecture](./architecture.md) principle of "play within 3 taps," these endpoints support the minimal-step onboarding flow.

**Pattern**:
```typescript
// POST /api/profiles - Create profile (onboarding)
// Returns: Created profile with id

// GET /api/profiles/me - Get current user's profile
// Returns: Full profile or 404 if not created

// PATCH /api/profiles/me - Update profile
// Accepts: Partial profile fields
// Returns: Updated profile

// DELETE /api/profiles/me - Delete profile
// Returns: 204 No Content
```

**Validation rules**:
- `displayName`: 2-100 characters, no excessive whitespace
- `bio`: Max 200 characters (optional)
- `availability`: At least one window required
- `homeCourtLocation`: Valid lat/lng range

---

### Step 4: Implement Profile Creation UI

**File**: `src/screens/ProfileCreate.tsx` (or framework equivalent)

**Purpose**: Guide new users through profile setup in 3 focused steps

Per [Architecture](./architecture.md): "Mobile-first, one-handed phone use at the court." Design for thumb reach zones.

**Flow**:
```
Step 1: Skill & Style
┌─────────────────────────┐
│  What's your level?     │
│                         │
│  ○ Beginner             │
│  ○ Intermediate         │
│  ● Advanced             │
│  ○ Competitive          │
│                         │
│  How do you play?       │
│  [Singles] [Doubles] [Both]
│                         │
│        [Continue →]     │
└─────────────────────────┘

Step 2: Home Court
┌─────────────────────────┐
│  Where do you play?     │
│                         │
│  [🔍 Search courts...  ]│
│                         │
│  ┌───────────────────┐  │
│  │     [Map View]    │  │
│  │        📍         │  │
│  └───────────────────┘  │
│                         │
│  Riverside Tennis Club  │
│        [Continue →]     │
└─────────────────────────┘

Step 3: Availability
┌─────────────────────────┐
│  When can you play?     │
│                         │
│  [+ Add time slot]      │
│                         │
│  ┌─────────────────────┐│
│  │ Sat  9am - 12pm  ✕ ││
│  │ Sun  2pm - 5pm   ✕ ││
│  └─────────────────────┘│
│                         │
│     [Complete Setup]    │
└─────────────────────────┘
```

**Implementation notes**:
- Use location autocomplete (Google Places or similar) for court search
- Time slots use simple hour pickers, not minute precision
- Allow skipping bio on initial setup (can add later)
- Progress indicator shows 3 steps total

---

### Step 5: Add Profile Edit Screen

**File**: `src/screens/ProfileEdit.tsx`

**Purpose**: Allow users to update their profile after creation

**Pattern**:
```
┌─────────────────────────┐
│  ← Edit Profile         │
│─────────────────────────│
│  Display Name           │
│  [Alex T.             ] │
│                         │
│  Skill Level            │
│  [Advanced         ▼]   │
│                         │
│  Play Style             │
│  [Both             ▼]   │
│                         │
│  Home Court             │
│  Riverside Tennis Club  │
│  [Change]               │
│                         │
│  Availability           │
│  Sat 9am-12pm, Sun 2-5pm│
│  [Edit]                 │
│                         │
│  Bio                    │
│  [Looking for rallying  │
│   partners. 3.5 NTRP   ]│
│                         │
│       [Save Changes]    │
└─────────────────────────┘
```

Auto-save on field blur is nice but can cause confusion. Use explicit save button for MVP.

---

### Step 6: Wire Up Navigation

**File**: `src/navigation/index.ts`

**Purpose**: Integrate profile screens into app flow

**Pattern**:
```typescript
// Auth flow check
if (!user) {
  return <AuthStack />;
}

if (!userHasProfile) {
  return <ProfileCreateStack />;  // Onboarding flow
}

return <MainStack />;  // Discovery, matches, settings
```

New users are routed to profile creation before accessing the main app. This ensures all users have complete profiles before entering the matching pool.

---

## Verification

How to verify this implementation works:

```bash
# 1. Run migrations
npm run db:migrate

# 2. Start the app
npm run dev

# 3. Create a test user and complete onboarding
# - Navigate through all 3 profile steps
# - Verify profile saves correctly

# 4. Test API directly
curl -X GET http://localhost:3000/api/profiles/me \
  -H "Authorization: Bearer <token>"
  
# Expected: Full profile JSON with all fields populated
```

**Expected Result**:
- New users see profile creation flow on first login
- All profile fields persist correctly
- Profile edit screen shows saved values
- Location search returns valid court results
- Availability windows can be added/removed

**Manual QA checklist**:
- [ ] Can complete onboarding in under 2 minutes
- [ ] All skill levels selectable
- [ ] Map shows correct location for selected court
- [ ] At least one availability slot required
- [ ] Edit screen reflects all saved data
- [ ] Works on mobile viewport (375px width)

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 1 as done
2. Proceed to **Task 2: Discovery/Matching** — which will use profiles for proximity and compatibility matching

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale and mobile-first principles
- [Epic](./epic.md) – Task scope and MVP definition
- [Timeline](./timeline.md) – Status tracking