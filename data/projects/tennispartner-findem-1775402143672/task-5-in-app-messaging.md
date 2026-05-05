# 🛠️ Task 5: In-App Messaging

**Purpose**: Enable connected players to communicate directly within the app to coordinate match details, confirm availability, and finalize logistics without exchanging personal contact information.

**Effort**: 2 days

**Dependencies**: Task 3 (Connection Flow) must be complete—messaging only available between connected players

**Parallel With**: Task 6 (Push Notifications) can start alongside once message creation endpoint exists

**Blocks**: Push notifications for new messages, future features like match scheduling

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Conversation list showing all active chats
- 1:1 message thread between connected players
- Real-time message delivery via WebSocket
- Message persistence and read status
- Basic typing indicators

### What's NOT Included
- Group messaging — connections are 1:1 only
- Rich media (images, voice) — text suffices for MVP
- Message reactions/emoji — adds complexity without value
- Push notifications — deferred to Task 6
- Message search — premature optimization

---

## Prerequisites

Before starting:
- Connection system operational (users can connect/accept)
- WebSocket infrastructure decision made (Socket.io vs native WS)
- Familiarity with real-time messaging patterns

---

## Implementation Steps

### Step 1: Database Schema for Messages

**File**: `prisma/schema.prisma` (or equivalent migration)

**Purpose**: Define conversation and message storage with efficient querying

Conversations are implicit—derived from the connection. We store messages with sender, receiver, content, and timestamps. The `read_at` field enables read receipts without a separate table.

**Pattern**:
```prisma
model Message {
  id          String    @id @default(cuid())
  senderId    String
  receiverId  String
  content     String    @db.Text
  createdAt   DateTime  @default(now())
  readAt      DateTime?
  
  sender      User      @relation("SentMessages", fields: [senderId], references: [id])
  receiver    User      @relation("ReceivedMessages", fields: [receiverId], references: [id])
  
  @@index([senderId, receiverId, createdAt])
  @@index([receiverId, readAt])
}
```

Key decision: No separate `Conversation` table. The connection itself implies the conversation. Query messages where `(senderId, receiverId)` matches the connection pair.

### Step 2: Message API Endpoints

**File**: `src/routes/messages.ts`

**Purpose**: REST endpoints for message CRUD and conversation listing

Three endpoints handle all messaging needs:
1. GET conversations list (recent message per connection)
2. GET messages for a specific connection
3. POST new message

**Pattern**:
```typescript
// GET /api/messages/conversations
// Returns list of connections with last message preview
async function getConversations(userId: string) {
  const connections = await getAcceptedConnections(userId);
  
  return Promise.all(connections.map(async (conn) => {
    const partnerId = conn.requesterId === userId ? conn.receiverId : conn.requesterId;
    const lastMessage = await getLastMessage(userId, partnerId);
    const unreadCount = await getUnreadCount(userId, partnerId);
    
    return {
      partnerId,
      partnerName: conn.partner.name,
      partnerAvatar: conn.partner.avatar,
      lastMessage: lastMessage?.content?.slice(0, 50),
      lastMessageAt: lastMessage?.createdAt,
      unreadCount
    };
  }));
}

// GET /api/messages/:partnerId
// Returns paginated messages with a connected partner
async function getMessages(userId: string, partnerId: string, cursor?: string) {
  // Verify connection exists first
  const connected = await verifyConnection(userId, partnerId);
  if (!connected) throw new ForbiddenError('Not connected');
  
  return prisma.message.findMany({
    where: {
      OR: [
        { senderId: userId, receiverId: partnerId },
        { senderId: partnerId, receiverId: userId }
      ]
    },
    orderBy: { createdAt: 'desc' },
    take: 50,
    cursor: cursor ? { id: cursor } : undefined
  });
}

// POST /api/messages/:partnerId
async function sendMessage(userId: string, partnerId: string, content: string) {
  const connected = await verifyConnection(userId, partnerId);
  if (!connected) throw new ForbiddenError('Not connected');
  
  const message = await prisma.message.create({
    data: { senderId: userId, receiverId: partnerId, content }
  });
  
  // Emit to WebSocket for real-time delivery
  emitToUser(partnerId, 'new_message', message);
  
  return message;
}
```

### Step 3: WebSocket Real-Time Layer

**File**: `src/websocket/messaging.ts`

**Purpose**: Enable instant message delivery and typing indicators

WebSocket handles three event types: new messages, read receipts, and typing indicators. Keep the protocol simple—complex features can layer on later.

**Pattern**:
```typescript
// Server-side WebSocket handler
io.on('connection', (socket) => {
  const userId = socket.handshake.auth.userId;
  
  // Join user's personal room for direct messaging
  socket.join(`user:${userId}`);
  
  // Handle typing indicator
  socket.on('typing', ({ partnerId }) => {
    io.to(`user:${partnerId}`).emit('partner_typing', { userId });
  });
  
  // Handle read receipt
  socket.on('mark_read', async ({ partnerId }) => {
    await prisma.message.updateMany({
      where: {
        senderId: partnerId,
        receiverId: userId,
        readAt: null
      },
      data: { readAt: new Date() }
    });
    
    io.to(`user:${partnerId}`).emit('messages_read', { by: userId });
  });
});

// Helper to emit to specific user
function emitToUser(userId: string, event: string, data: any) {
  io.to(`user:${userId}`).emit(event, data);
}
```

### Step 4: Conversation List UI

**File**: `src/components/ConversationList.tsx`

**Purpose**: Display all active conversations with unread indicators

The conversation list is the messaging entry point. Show partner photo, name, message preview, and time. Unread count badge draws attention to new messages.

**Pattern**:
```tsx
function ConversationList() {
  const { data: conversations } = useQuery(['conversations'], fetchConversations);
  
  return (
    <div className="divide-y">
      {conversations?.map((conv) => (
        <Link 
          key={conv.partnerId} 
          to={`/messages/${conv.partnerId}`}
          className="flex items-center p-4 hover:bg-gray-50"
        >
          <Avatar src={conv.partnerAvatar} className="w-12 h-12" />
          <div className="ml-3 flex-1 min-w-0">
            <div className="flex justify-between">
              <span className="font-medium">{conv.partnerName}</span>
              <span className="text-sm text-gray-500">
                {formatRelativeTime(conv.lastMessageAt)}
              </span>
            </div>
            <p className="text-sm text-gray-600 truncate">
              {conv.lastMessage}
            </p>
          </div>
          {conv.unreadCount > 0 && (
            <Badge variant="primary">{conv.unreadCount}</Badge>
          )}
        </Link>
      ))}
    </div>
  );
}
```

### Step 5: Message Thread UI

**File**: `src/components/MessageThread.tsx`

**Purpose**: Display and send messages in a conversation

Standard chat interface: messages scroll up, input fixed at bottom, own messages right-aligned, partner's left-aligned. Auto-scroll on new messages but not if user scrolled up to read history.

**Pattern**:
```tsx
function MessageThread({ partnerId }: { partnerId: string }) {
  const [message, setMessage] = useState('');
  const { data: messages, fetchNextPage } = useInfiniteQuery(
    ['messages', partnerId],
    ({ pageParam }) => fetchMessages(partnerId, pageParam)
  );
  const sendMutation = useMutation(sendMessage);
  
  // WebSocket subscription for real-time updates
  useEffect(() => {
    const socket = getSocket();
    
    socket.on('new_message', (msg) => {
      if (msg.senderId === partnerId) {
        queryClient.setQueryData(['messages', partnerId], (old) => 
          addMessageToCache(old, msg)
        );
        socket.emit('mark_read', { partnerId });
      }
    });
    
    return () => socket.off('new_message');
  }, [partnerId]);
  
  const handleSend = () => {
    if (!message.trim()) return;
    sendMutation.mutate({ partnerId, content: message });
    setMessage('');
  };
  
  return (
    <div className="flex flex-col h-full">
      {/* Messages (reverse order for bottom-up scroll) */}
      <div className="flex-1 overflow-y-auto flex flex-col-reverse p-4">
        {messages?.pages.flatMap(page => page).map((msg) => (
          <MessageBubble 
            key={msg.id}
            content={msg.content}
            isOwn={msg.senderId !== partnerId}
            time={msg.createdAt}
          />
        ))}
      </div>
      
      {/* Input */}
      <div className="border-t p-4 flex gap-2">
        <Input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Type a message..."
          className="flex-1"
        />
        <Button onClick={handleSend} disabled={!message.trim()}>
          Send
        </Button>
      </div>
    </div>
  );
}
```

### Step 6: Typing Indicator

**File**: `src/hooks/useTypingIndicator.ts`

**Purpose**: Show when partner is typing, debounced to avoid flicker

Typing indicators add presence without complexity. Debounce emissions to avoid flooding. Auto-clear after 3 seconds of inactivity.

**Pattern**:
```typescript
function useTypingIndicator(partnerId: string) {
  const [partnerTyping, setPartnerTyping] = useState(false);
  const socket = getSocket();
  
  // Emit own typing status (debounced)
  const emitTyping = useMemo(
    () => debounce(() => socket.emit('typing', { partnerId }), 300),
    [partnerId]
  );
  
  // Listen for partner typing
  useEffect(() => {
    let timeout: NodeJS.Timeout;
    
    socket.on('partner_typing', ({ userId }) => {
      if (userId === partnerId) {
        setPartnerTyping(true);
        clearTimeout(timeout);
        timeout = setTimeout(() => setPartnerTyping(false), 3000);
      }
    });
    
    return () => {
      socket.off('partner_typing');
      clearTimeout(timeout);
    };
  }, [partnerId]);
  
  return { partnerTyping, emitTyping };
}
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Run the test suite
npm test -- --grep "messaging"

# 2. Manual verification flow:
# - Connect two test accounts
# - Open messages on both devices/browsers
# - Send message from User A → verify appears instantly on User B
# - Verify unread count shows on conversation list
# - Open thread on User B → verify read receipt sent
# - Type on User A → verify typing indicator on User B
```

**Expected Result**: 
- Messages deliver in <500ms (WebSocket latency)
- Conversation list shows accurate unread counts
- Read receipts update without page refresh
- Typing indicator appears within 300ms of keystroke

---

## Edge Cases to Handle

| Scenario | Handling |
|----------|----------|
| User offline when message sent | Message persists in DB, delivered when they reconnect |
| Connection removed mid-conversation | Archive conversation, block new messages |
| Rapid message sending | Debounce UI, no server-side rate limit for MVP |
| Very long messages | Truncate at 2000 chars client-side |

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 5 complete
2. Proceed to Task 6 (Push Notifications) to alert users of new messages
3. Consider adding message timestamps grouping ("Today", "Yesterday") as polish

---

## Related Documents

- [Architecture](./architecture.md) – WebSocket infrastructure decisions
- [Epic](./epic.md) – Messaging scope and deferral rationale
- [Timeline](./timeline.md) – Status tracking