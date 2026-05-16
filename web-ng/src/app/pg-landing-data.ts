/**
 * Static content arrays for the PgLandingShowcaseComponent.
 * All landing page copy lives here — no magic strings in the component.
 */

// ── Output Cards ─────────────────────────────────────────────────────────────

export interface OutputCard {
  icon: string;
  filename: string;
  description: string;
}

export const OUTPUT_CARDS: OutputCard[] = [
  {
    icon: '◎',
    filename: 'analysis.md',
    description:
      'Problem space dissection, market context, constraints, and risk surface — everything you need before writing a single line of code.',
  },
  {
    icon: '◈',
    filename: 'epic.md',
    description:
      'User stories, acceptance criteria, and scope boundaries structured so any developer can estimate and begin without a kickoff meeting.',
  },
  {
    icon: '◆',
    filename: 'architecture.md',
    description:
      'Tech stack decision, data model, API surface, and system topology with rationale — the blueprint that outlasts the sprint.',
  },
  {
    icon: '◉',
    filename: 'timeline.md',
    description:
      'Phase breakdown, milestones, and sequencing with realistic duration estimates derived directly from the architecture.',
  },
  {
    icon: '◇',
    filename: 'implementation-guide.md',
    description:
      'Ordered tasks, code entry points, and effort estimates that turn the spec into a developer backlog on day one.',
  },
];

// ── How-It-Works Steps ───────────────────────────────────────────────────────

export interface HowItWorksStep {
  number: string;
  title: string;
  body: string;
  excerpt: string;
  excerptLabel: string;
}

export const HOW_IT_WORKS_STEPS: HowItWorksStep[] = [
  {
    number: '01',
    title: 'Braindump',
    body: 'Write freely. Paste a rough stream-of-consciousness description of what you want to build — spelling mistakes, incomplete sentences, contradictions and all. Specview is built to read messy human thought, not polished requirements.',
    excerpt:
      'ok so i want to build this thing where users can paste like a big messy brain dump of their idea — doesnt matter how rough — and then the system figures out what theyre actually trying to build and spits out like a full spec document set...',
    excerptLabel: 'Sample braindump input',
  },
  {
    number: '02',
    title: 'Generate',
    body: 'Click generate. In under a minute an AI pipeline reads your braindump, structures the problem, makes architecture decisions, and writes five interlocking documents — each building on the last. Average generation time: 44.5 seconds.',
    excerpt:
      '## Executive Summary\n\nThe existing checkout flow has accumulated significant technical debt. Conversion rates have dropped 4.2% quarter-over-quarter. The root cause is a fragmented frontend built across four frameworks — an inheritance from two acquisitions...',
    excerptLabel: 'From the generated analysis.md',
  },
  {
    number: '03',
    title: 'Implement',
    body: 'Open the implementation guide and start building. Every task is ordered, estimated, and linked to the architecture and epic. Hand it to a developer or feed it into an AI coding assistant — either way, the spec does the thinking so you can focus on shipping.',
    excerpt:
      'Task 1 — Database schema migration [2 days]\nAdd `checkout_session` table with FK to `user`. Index on `status` + `created_at`. Migration script in `/db/migrations/`.\n\nTask 2 — Stripe Elements integration [3 days]\nReplace current card form with Stripe.js iframe...',
    excerptLabel: 'From the generated implementation-guide.md',
  },
];

// ── Comparison Table ─────────────────────────────────────────────────────────

export interface ComparisonRow {
  dimension: string;
  competitor: string;
  specview: string;
}

export const COMPARISON_ROWS: ComparisonRow[] = [
  {
    dimension: 'Input',
    competitor: 'Structured form, explicit fields, precise prompts required',
    specview: 'Free-form braindump — any format, any length, any messiness',
  },
  {
    dimension: 'Output',
    competitor: 'Generated UI code or boilerplate scaffolding',
    specview: 'Five interlocking spec documents: analysis, epic, architecture, timeline, guide',
  },
  {
    dimension: 'Architecture',
    competitor: 'Assumed stack (React + Tailwind, no negotiation)',
    specview: 'Reasoned recommendation with rationale; your stack, your constraints',
  },
  {
    dimension: 'Docs',
    competitor: 'Inline comments and README snippets scattered through generated code',
    specview: 'Standalone markdown files a developer can read and act on independently',
  },
  {
    dimension: 'Quality gate',
    competitor: 'Ship code first, discover design problems later',
    specview: 'Design problems surfaced in the analysis before a single line of code',
  },
  {
    dimension: 'Pricing',
    competitor: '$20–50/month subscription with seat-based limits',
    specview: 'Free tier available; Pro at a fraction of the cost',
  },
];

// ── Pricing Tiers ─────────────────────────────────────────────────────────────

export interface PricingTier {
  name: string;
  price: string;
  priceSuffix: string;
  description: string;
  features: string[];
  ctaLabel: string;
  isPrimary: boolean;
}

export const PRICING_TIERS: PricingTier[] = [
  {
    name: 'Free',
    price: '$0',
    priceSuffix: 'forever',
    description: 'Everything you need to evaluate the pipeline and ship your first spec.',
    features: [
      '5 spec generations per month',
      'All five document types',
      'Analysis, epic, architecture, timeline, guide',
      'Markdown export',
      'Community support',
    ],
    ctaLabel: 'Start for free',
    isPrimary: false,
  },
  {
    name: 'Pro',
    price: '$12',
    priceSuffix: 'per month',
    description: 'Unlimited generations and priority processing for teams that ship continuously.',
    features: [
      'Unlimited spec generations',
      'Priority queue — no waiting',
      'All five document types',
      'Project history and archive',
      'Email support with 24h SLA',
    ],
    ctaLabel: 'Upgrade to Pro',
    isPrimary: true,
  },
];

// ── FAQ Items ─────────────────────────────────────────────────────────────────

export interface FaqItem {
  question: string;
  answer: string;
}

export const FAQ_ITEMS: FaqItem[] = [
  {
    question: 'How messy can my braindump actually be?',
    answer:
      'Very messy. The pipeline is specifically tuned for unstructured human thought — bullet points, stream of consciousness, half-sentences, contradictions. The analysis step is designed to find the signal in the noise. If you can explain your idea to a colleague in words, Specview can work with it.',
  },
  {
    question: 'What kinds of projects does it work for?',
    answer:
      'Any software project: web apps, mobile apps, APIs, internal tools, data pipelines, browser extensions. The pipeline produces technology-agnostic specs first, then makes architecture recommendations based on your constraints. It is not limited to web development.',
  },
  {
    question: 'How long does generation actually take?',
    answer:
      'The current average is 44.5 seconds across all five documents. Longer braindumps take slightly longer because the analysis step scales with input length. Pro tier gets priority queue access, so generation starts immediately without waiting for free-tier capacity.',
  },
  {
    question: 'Can I use the generated specs with AI coding assistants?',
    answer:
      'Yes — that is exactly the intended workflow. The implementation guide is structured so you can feed individual tasks to Claude, Copilot, or Cursor with full context from the architecture doc. The spec does the thinking; the coding assistant does the typing.',
  },
  {
    question: 'Is my braindump stored? Who can see it?',
    answer:
      'Your braindumps and generated specs are stored in your account only. They are not used to train any model. You can delete a project at any time and all associated data is removed immediately. Self-hosted deployment is available on request.',
  },
  {
    question: 'What if the generated spec gets something wrong?',
    answer:
      'The spec is a starting point, not a contract. Every document is markdown you can edit directly. In practice the architecture recommendations are accurate enough to proceed without changes roughly 80% of the time; the remaining 20% need minor constraint corrections before handoff.',
  },
  {
    question: 'Does Specview write code?',
    answer:
      'No — Specview writes specs. Code generation is deliberately out of scope. The thesis is that a well-structured spec is more valuable than generated boilerplate because it outlasts the first sprint and gives every team member a shared mental model of what you are building.',
  },
];

// ── Pull Quotes ───────────────────────────────────────────────────────────────

export interface PullQuote {
  text: string;
  attribution: string;
}

export const PULL_QUOTES: PullQuote[] = [
  {
    text: 'I pasted two paragraphs of stream-of-consciousness and got back an architecture doc I would have spent half a day writing.',
    attribution: 'Founder, B2B SaaS startup',
  },
  {
    text: 'The analysis step caught a fundamental scope problem before we wrote any code. That alone was worth the time.',
    attribution: 'CTO, early-stage startup',
  },
  {
    text: 'Feeding the implementation guide into Cursor with the architecture doc as context cut our sprint planning from three hours to thirty minutes.',
    attribution: 'Lead engineer, growth-stage company',
  },
  {
    text: 'The epic it generates is more structured than what most product managers produce manually.',
    attribution: 'Engineering manager, fintech',
  },
];
