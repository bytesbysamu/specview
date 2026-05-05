# 🛠️ Task 4: Connection Requests

**Purpose**: Enable players to initiate matches by sending connection requests with proposed time/location, and allow recipients to accept, decline, or counter-propose.

**Effort**: 3 days

**Dependencies**: Task 3 (Discovery/Search) — need player discovery to find someone to connect with

**Parallel With**: —

**Blocks**: Task 5 (Messaging) — chat unlocks after connection accepted

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Connection request data model (pending/accepted/declined states)
- API endpoints for send, accept, decline, counter-propose
- Request inbox UI for viewing pending requests
- Send request flow from player profile
- Push notification triggers (implementation in Task 6)

### What's NOT Included
- Chat/messaging — separate task, unlocks after accept
- Notification delivery — Task 6 handles push infrastructure
- Calendar integration — future enhancement
- Request expiration/auto-decline — keep MVP simple

---

## Prerequisites

Before starting:
- Task 3 complete (can discover and view player profiles)
- Database migrations working
- Authentication in place (know who's sending/receiving)

---

## Implementation Steps

### Step 1: Connection Request Schema

**File**: `prisma/schema.prisma` (or equivalent ORM)

**Purpose**: Define the data model for connection requests

The request captures who's asking, who's being asked, and the proposed match details. State machine is intentionally simple: `pending` → `accepted` | `declined`.

**Pattern**:
```prisma
model ConnectionRequest {
  id            String   @id @default(cuid())
  fromPlayerId  String
  toPlayerId    String
  status        RequestStatus @default(PENDING)
  
  // Proposed match details
  proposedDate  DateTime
  proposedTime  String   // "morning" | "afternoon" | "evening" or specific time
  proposedVenue String?  // Optional - can be decided later
  message       String?  // "Want to hit some balls Saturday?"
  
  // Counter-proposal (if declined with alternative)
  counterDate   DateTime?
  counterTime   String?
  counterVenue  String?
  
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt
  
  fromPlayer    Player   @relation("SentRequests", fields: [fromPlayerId], references: [id])
  toPlayer      Player   @relation("ReceivedRequests", fields: [toPlayerId], references: [id])
  
  @@unique([fromPlayerId, toPlayerId, status]) // One pending request per pair
}

enum RequestStatus {
  PENDING
  ACCEPTED
  DECLINED
  COUNTERED  // Declined but with alternative proposal
}
```

### Step 2: Connection Request API

**File**: `src/routes/connections.ts`

**Purpose**: CRUD operations for connection requests

Four endpoints: send request, get my requests (inbox), respond to request, get request details.

**Pattern**:
```typescript
// POST /api/connections/request
// Send a new connection request
async function sendRequest(req: Request) {
  const { toPlayerId, proposedDate, proposedTime, proposedVenue, message } = req.body;
  const fromPlayerId = req.user.id;
  
  // Validation
  if (fromPlayerId === toPlayerId) {
    throw new BadRequest("Cannot send request to yourself");
  }
  
  // Check for existing pending request in either direction
  const existing = await db.connectionRequest.findFirst({
    where: {
      OR: [
        { fromPlayerId, toPlayerId, status: 'PENDING' },
        { fromPlayerId: toPlayerId, toPlayerId: fromPlayerId, status: 'PENDING' }
      ]
    }
  });
  
  if (existing) {
    throw new Conflict("Pending request already exists between these players");
  }
  
  const request = await db.connectionRequest.create({
    data: { fromPlayerId, toPlayerId, proposedDate, proposedTime, proposedVenue, message }
  });
  
  // Trigger notification (handled by Task 6)
  await notificationService.queue('CONNECTION_REQUEST', toPlayerId, { requestId: request.id });
  
  return request;
}

// GET /api/connections/inbox
// Get requests where I'm the recipient
async function getInbox(req: Request) {
  const playerId = req.user.id;
  
  return db.connectionRequest.findMany({
    where: { toPlayerId: playerId },
    include: { fromPlayer: { select: { id: true, name: true, skillLevel: true, photo: true } } },
    orderBy: { createdAt: 'desc' }
  });
}

// GET /api/connections/sent
// Get requests I've sent
async function getSent(req: Request) {
  const playerId = req.user.id;
  
  return db.connectionRequest.findMany({
    where: { fromPlayerId: playerId },
    include: { toPlayer: { select: { id: true, name: true, skillLevel: true, photo: true } } },
    orderBy: { createdAt: 'desc' }
  });
}

// POST /api/connections/:requestId/respond
// Accept, decline, or counter-propose
async function respondToRequest(req: Request) {
  const { requestId } = req.params;
  const { action, counterDate, counterTime, counterVenue } = req.body;
  const playerId = req.user.id;
  
  const request = await db.connectionRequest.findUnique({ where: { id: requestId } });
  
  if (!request || request.toPlayerId !== playerId) {
    throw new NotFound("Request not found");
  }
  
  if (request.status !== 'PENDING') {
    throw new BadRequest("Request already resolved");
  }
  
  let status: RequestStatus;
  let updateData: any = {};
  
  switch (action) {
    case 'accept':
      status = 'ACCEPTED';
      break;
    case 'decline':
      status = 'DECLINED';
      break;
    case 'counter':
      status = 'COUNTERED';
      updateData = { counterDate, counterTime, counterVenue };
      break;
    default:
      throw new BadRequest("Invalid action");
  }
  
  const updated = await db.connectionRequest.update({
    where: { id: requestId },
    data: { status, ...updateData }
  });
  
  // Notify the original sender
  await notificationService.queue('CONNECTION_RESPONSE', request.fromPlayerId, {
    requestId,
    status,
    responderId: playerId
  });
  
  return updated;
}
```

### Step 3: Request Inbox Component

**File**: `src/components/ConnectionInbox.tsx`

**Purpose**: Display pending requests with accept/decline actions

Mobile-first design: swipe actions or clear tap targets. Show sender info, proposed time, and quick actions.

**Pattern**:
```tsx
function ConnectionInbox() {
  const { data: requests, isLoading } = useQuery(['inbox'], fetchInbox);
  const respondMutation = useMutation(respondToRequest);
  
  if (isLoading) return <LoadingSpinner />;
  
  const pending = requests?.filter(r => r.status === 'PENDING') || [];
  
  if (pending.length === 0) {
    return <EmptyState message="No pending requests" icon={<InboxIcon />} />;
  }
  
  return (
    <div className="space-y-3">
      {pending.map(request => (
        <RequestCard
          key={request.id}
          request={request}
          onAccept={() => respondMutation.mutate({ requestId: request.id, action: 'accept' })}
          onDecline={() => respondMutation.mutate({ requestId: request.id, action: 'decline' })}
          onCounter={() => openCounterModal(request)}
        />
      ))}
    </div>
  );
}

function RequestCard({ request, onAccept, onDecline, onCounter }) {
  const { fromPlayer, proposedDate, proposedTime, proposedVenue, message } = request;
  
  return (
    <div className="bg-white rounded-lg p-4 shadow-sm">
      <div className="flex items-center gap-3 mb-3">
        <Avatar src={fromPlayer.photo} name={fromPlayer.name} />
        <div>
          <p className="font-medium">{fromPlayer.name}</p>
          <p className="text-sm text-gray-500">{fromPlayer.skillLevel}</p>
        </div>
      </div>
      
      <div className="mb-3 text-sm">
        <p><CalendarIcon className="inline w-4 h-4 mr-1" />{formatDate(proposedDate)}</p>
        <p><ClockIcon className="inline w-4 h-4 mr-1" />{proposedTime}</p>
        {proposedVenue && <p><MapPinIcon className="inline w-4 h-4 mr-1" />{proposedVenue}</p>}
        {message && <p className="mt-2 italic">"{message}"</p>}
      </div>
      
      {/* Large tap targets for mobile */}
      <div className="flex gap-2">
        <Button onClick={onAccept} variant="primary" className="flex-1">Accept</Button>
        <Button onClick={onCounter} variant="secondary" className="flex-1">Counter</Button>
        <Button onClick={onDecline} variant="ghost" className="px-3">
          <XIcon className="w-5 h-5" />
        </Button>
      </div>
    </div>
  );
}
```

### Step 4: Send Request Flow

**File**: `src/components/PlayerProfile.tsx` (add to existing)

**Purpose**: Add "Connect" button to player profiles with request modal

Triggered from discovery results. Opens modal to propose time/location.

**Pattern**:
```tsx
function PlayerProfile({ player }) {
  const [showRequestModal, setShowRequestModal] = useState(false);
  
  return (
    <div>
      {/* Existing profile content */}
      <ProfileHeader player={player} />
      <SkillDetails player={player} />
      <Availability player={player} />
      
      {/* Connect action - prominent placement */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-white border-t">
        <Button 
          onClick={() => setShowRequestModal(true)}
          variant="primary"
          className="w-full py-3 text-lg"
        >
          Request to Play
        </Button>
      </div>
      
      <RequestModal
        isOpen={showRequestModal}
        onClose={() => setShowRequestModal(false)}
        toPlayer={player}
      />
    </div>
  );
}

function RequestModal({ isOpen, onClose, toPlayer }) {
  const [date, setDate] = useState<Date | null>(null);
  const [time, setTime] = useState('');
  const [venue, setVenue] = useState('');
  const [message, setMessage] = useState('');
  
  const sendMutation = useMutation(sendConnectionRequest, {
    onSuccess: () => {
      toast.success('Request sent!');
      onClose();
    }
  });
  
  const handleSubmit = () => {
    if (!date || !time) {
      toast.error('Please select date and time');
      return;
    }
    sendMutation.mutate({
      toPlayerId: toPlayer.id,
      proposedDate: date,
      proposedTime: time,
      proposedVenue: venue || undefined,
      message: message || undefined
    });
  };
  
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Play with ${toPlayer.name}`}>
      <div className="space-y-4">
        <DatePicker
          label="When?"
          value={date}
          onChange={setDate}
          minDate={new Date()}
        />
        
        <TimeSlotPicker
          label="What time?"
          value={time}
          onChange={setTime}
          options={['Morning', 'Afternoon', 'Evening']}
        />
        
        <Input
          label="Where? (optional)"
          value={venue}
          onChange={setVenue}
          placeholder="Court or area name"
        />
        
        <Textarea
          label="Message (optional)"
          value={message}
          onChange={setMessage}
          placeholder="Looking forward to hitting!"
          maxLength={200}
        />
        
        <Button
          onClick={handleSubmit}
          loading={sendMutation.isLoading}
          className="w-full"
        >
          Send Request
        </Button>
      </div>
    </Modal>
  );
}
```

### Step 5: Counter-Proposal Flow

**File**: `src/components/CounterProposalModal.tsx`

**Purpose**: Allow declining with an alternative suggestion

Same form as request modal, but pre-filled with context and different submit action.

**Pattern**:
```tsx
function CounterProposalModal({ isOpen, onClose, originalRequest }) {
  // Pre-fill with original proposal as starting point
  const [date, setDate] = useState(originalRequest.proposedDate);
  const [time, setTime] = useState(originalRequest.proposedTime);
  const [venue, setVenue] = useState(originalRequest.proposedVenue || '');
  
  const counterMutation = useMutation(
    (data) => respondToRequest({ 
      requestId: originalRequest.id, 
      action: 'counter',
      ...data 
    }),
    { onSuccess: () => { toast.success('Counter-proposal sent'); onClose(); } }
  );
  
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Suggest Different Time">
      <p className="text-sm text-gray-600 mb-4">
        {originalRequest.fromPlayer.name} proposed {formatDate(originalRequest.proposedDate)} {originalRequest.proposedTime}
      </p>
      
      {/* Same form fields as RequestModal */}
      <DatePicker value={date} onChange={setDate} />
      <TimeSlotPicker value={time} onChange={setTime} />
      <Input value={venue} onChange={setVenue} placeholder="Where?" />
      
      <Button onClick={() => counterMutation.mutate({ counterDate: date, counterTime: time, counterVenue: venue })}>
        Send Counter-Proposal
      </Button>
    </Modal>
  );
}
```

### Step 6: Navigation Integration

**File**: `src/components/Navigation.tsx`

**Purpose**: Add inbox badge showing pending request count

Users need visibility into pending requests from anywhere in the app.

**Pattern**:
```tsx
function Navigation() {
  const { data: inbox } = useQuery(['inbox'], fetchInbox, {
    refetchInterval: 30000 // Poll every 30s for new requests
  });
  
  const pendingCount = inbox?.filter(r => r.status === 'PENDING').length || 0;
  
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t flex justify-around py-2">
      <NavItem to="/discover" icon={<SearchIcon />} label="Find" />
      <NavItem to="/inbox" icon={<InboxIcon />} label="Requests" badge={pendingCount} />
      <NavItem to="/matches" icon={<UsersIcon />} label="Matches" />
      <NavItem to="/profile" icon={<UserIcon />} label="Profile" />
    </nav>
  );
}

function NavItem({ to, icon, label, badge }) {
  return (
    <Link to={to} className="flex flex-col items-center relative">
      {icon}
      <span className="text-xs">{label}</span>
      {badge > 0 && (
        <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
          {badge > 9 ? '9+' : badge}
        </span>
      )}
    </Link>
  );
}
```

---

## Verification

How to verify this implementation works:

```bash
# Run database migration
npx prisma migrate dev --name add-connection-requests

# Start the app
npm run dev

# Test the API endpoints
curl -X POST http://localhost:3000/api/connections/request \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"toPlayerId": "player-123", "proposedDate": "2024-02-15", "proposedTime": "morning"}'

# Check inbox
curl http://localhost:3000/api/connections/inbox -H "Authorization: Bearer $TOKEN"
```

**Expected Result**:
1. Can send request from any player profile
2. Request appears in recipient's inbox with correct details
3. Accept → both players see in "Matches" list
4. Decline → request disappears, sender notified
5. Counter → sender receives alternative proposal
6. Badge count updates in real-time

**Manual Test Flow**:
1. Log in as Player A, discover Player B
2. Tap "Request to Play", fill in date/time, send
3. Log in as Player B, see request in inbox
4. Accept request
5. Verify both players can see connection in matches

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 4 done
2. Proceed to Task 5 (Messaging) — chat becomes available after connection accepted

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking