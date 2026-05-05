# 🛠️ Task 3: Landing Page + Waitlist

**Purpose**: Ship a conversion-focused landing page that communicates Trendfy's value proposition and captures email signups while demonstrating the concept with trend-to-outfit examples.

**Effort**: 1 day

**Dependencies**: None (can start immediately)

**Parallel With**: Task 1 (Data ingestion), Task 2 (Trend extraction)

**Blocks**: User acquisition, demand validation, beta user pool for launch

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Single-page landing site with hero, examples, and signup form
- Email capture with Supabase backend
- 3-5 static trend-to-outfit transformation examples
- Mobile-responsive design
- Basic analytics (page views, signup conversion)

### What's NOT Included
- User authentication — waitlist only, no accounts yet
- Dynamic trend content — examples are curated/static
- Payment integration — free waitlist, monetization comes later
- Email sequences — just capture, nurture campaigns follow

---

## Prerequisites

Before starting:
- Supabase project created (or reuse existing)
- Domain configured (trendfy.me or temporary subdomain)
- 3-5 curated trend examples with images (can be placeholder/mockup)
- Vercel or similar for deployment

---

## Implementation Steps

### Step 1: Project Setup

**File**: `landing/package.json`

**Purpose**: Initialize Next.js 14 project with minimal dependencies

```bash
npx create-next-app@latest landing --typescript --tailwind --app --no-src-dir
cd landing
npm install @supabase/supabase-js
```

Keep it minimal. No component libraries needed for a single page.

### Step 2: Supabase Waitlist Table

**File**: Supabase Dashboard → SQL Editor

**Purpose**: Create table to store email signups with metadata

```sql
create table waitlist (
  id uuid default gen_random_uuid() primary key,
  email text unique not null,
  source text default 'landing',
  created_at timestamp with time zone default now()
);

-- Enable RLS but allow anonymous inserts
alter table waitlist enable row level security;

create policy "Allow anonymous insert" on waitlist
  for insert with check (true);

-- Index for duplicate checking
create index waitlist_email_idx on waitlist(email);
```

### Step 3: Environment Configuration

**File**: `landing/.env.local`

**Purpose**: Configure Supabase connection

```
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

### Step 4: Supabase Client

**File**: `landing/lib/supabase.ts`

**Purpose**: Initialize Supabase client for browser use

```typescript
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)
```

### Step 5: Landing Page Structure

**File**: `landing/app/page.tsx`

**Purpose**: Single-page layout with all sections

The page follows a proven landing page structure:
1. **Hero** — Hook + primary CTA
2. **Problem** — Why existing solutions fail
3. **Solution** — How Trendfy works (3-step process)
4. **Examples** — Visual proof with trend transformations
5. **CTA** — Email capture form

```tsx
export default function Home() {
  return (
    <main className="min-h-screen">
      <Hero />
      <HowItWorks />
      <TrendExamples />
      <WaitlistForm />
      <Footer />
    </main>
  )
}
```

### Step 6: Hero Section

**File**: `landing/components/hero.tsx`

**Purpose**: Immediate value proposition and primary signup

Key copy elements:
- **Headline**: Focus on the outcome (discover trends, not "AI-powered platform")
- **Subhead**: Specificity builds trust ("from TikTok, Instagram, Pinterest")
- **CTA**: Low commitment ("Join the waitlist")

```tsx
export function Hero() {
  return (
    <section className="py-20 px-4 text-center">
      <h1 className="text-4xl md:text-6xl font-bold mb-6">
        Discover What's Actually Trending
        <br />
        <span className="text-purple-600">Before Everyone Else</span>
      </h1>
      <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
        AI scans TikTok, Instagram, and Pinterest to find emerging fashion trends.
        Get weekly drops of what's gaining momentum—with shoppable outfit links.
      </p>
      <WaitlistInput />
    </section>
  )
}
```

### Step 7: Email Capture Component

**File**: `landing/components/waitlist-input.tsx`

**Purpose**: Reusable signup form with loading/success states

```tsx
'use client'
import { useState } from 'react'
import { supabase } from '@/lib/supabase'

export function WaitlistInput() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setStatus('loading')
    
    const { error } = await supabase
      .from('waitlist')
      .insert({ email })
    
    if (error?.code === '23505') {
      // Already exists - treat as success
      setStatus('success')
    } else if (error) {
      setStatus('error')
    } else {
      setStatus('success')
    }
  }

  if (status === 'success') {
    return <p className="text-green-600 font-medium">You're on the list! 🎉</p>
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 max-w-md mx-auto">
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
        required
        className="flex-1 px-4 py-3 rounded-lg border"
      />
      <button
        type="submit"
        disabled={status === 'loading'}
        className="px-6 py-3 bg-purple-600 text-white rounded-lg font-medium"
      >
        {status === 'loading' ? '...' : 'Join Waitlist'}
      </button>
    </form>
  )
}
```

### Step 8: Trend Examples Section

**File**: `landing/components/trend-examples.tsx`

**Purpose**: Visual proof of concept with curated transformations

This is the most important section for conversion. Show, don't tell.

Each example shows:
- The trend (source content thumbnail + trend name)
- The outfit (styled look demonstrating the trend)
- Shop links (optional for MVP, can be placeholder)

```tsx
const examples = [
  {
    trend: 'Quiet Luxury',
    description: 'Understated elegance trending on TikTok',
    trendImage: '/examples/quiet-luxury-trend.jpg',
    outfitImage: '/examples/quiet-luxury-outfit.jpg',
    momentum: '+340% this month'
  },
  // 2-4 more examples
]

export function TrendExamples() {
  return (
    <section className="py-16 bg-gray-50">
      <h2 className="text-3xl font-bold text-center mb-12">
        From Trend to Outfit
      </h2>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto px-4">
        {examples.map((ex) => (
          <TrendCard key={ex.trend} {...ex} />
        ))}
      </div>
    </section>
  )
}
```

### Step 9: How It Works

**File**: `landing/components/how-it-works.tsx`

**Purpose**: Explain the process in 3 simple steps

```tsx
const steps = [
  { icon: '🔍', title: 'AI Scans', desc: 'We analyze millions of posts across platforms daily' },
  { icon: '📈', title: 'Trends Surface', desc: 'Our algorithms identify what\'s gaining real momentum' },
  { icon: '👗', title: 'You Shop', desc: 'Get curated outfits with direct purchase links' },
]

export function HowItWorks() {
  return (
    <section className="py-16 px-4">
      <div className="flex justify-center gap-8 md:gap-16">
        {steps.map((step, i) => (
          <div key={i} className="text-center max-w-xs">
            <div className="text-4xl mb-4">{step.icon}</div>
            <h3 className="font-bold mb-2">{step.title}</h3>
            <p className="text-gray-600 text-sm">{step.desc}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
```

### Step 10: Analytics Setup

**File**: `landing/app/layout.tsx`

**Purpose**: Basic tracking for conversion measurement

For MVP, Vercel Analytics or simple Plausible is sufficient:

```tsx
import { Analytics } from '@vercel/analytics/react'

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  )
}
```

### Step 11: Deploy

**Purpose**: Get live URL for sharing

```bash
# From landing directory
vercel --prod

# Or connect to GitHub for auto-deploys
vercel link
```

Configure custom domain in Vercel dashboard if ready.

---

## Verification

How to verify this implementation works:

```bash
# Local testing
npm run dev
# Visit http://localhost:3000

# Test signup flow
1. Enter email in form
2. Submit
3. Check Supabase table for new row

# Verify duplicate handling
1. Submit same email again
2. Should show success (not error)
```

**Expected Result**:
- Page loads in <2s
- Email submits successfully
- Success message displays
- Row appears in Supabase `waitlist` table
- Mobile layout works correctly

**Supabase verification**:
```sql
select * from waitlist order by created_at desc limit 10;
```

---

## Content Checklist

Before shipping, ensure:

- [ ] Hero headline is specific and outcome-focused
- [ ] 3-5 trend examples have real images (not placeholders)
- [ ] Mobile layout tested on actual device
- [ ] Meta tags set for social sharing (og:image, description)
- [ ] Favicon uploaded
- [ ] Privacy-friendly analytics enabled

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 3 done
2. Share landing page URL for feedback
3. Begin promoting on relevant channels (Reddit, Twitter, etc.)
4. Monitor signup rate to validate demand
5. Proceed to Task 4 (Email notifications) to set up waitlist nurturing

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking