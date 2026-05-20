The anonymous text box — what it is:

A visitor lands on specview.dev. Right there on the page, no signup, no account, no API key, they see a text area that says "Paste your messy thinking here." They paste anything — a startup idea, a feature plan, a life decision. They hit one button: "Analyze."

45 seconds later, the analysis appears below. Problems surfaced. Contradictions caught. Scope boundaries drawn. Open questions listed. The visitor just experienced the product without giving you their email.

Below the analysis: "Want the full spec? Epic, architecture, timeline, implementation guide. Sign up free."

That's the conversion moment. They've seen the value. Their own messy thinking came back structured. They want the rest.

How to build it:

Backend: One new Flask route. No auth required.

POST /api/public/analyze
Body: { "braindump": "..." }
Returns: { "analysis": "..." }

It runs only the analysis step of the pipeline. Not all five docs. One call, one document, one response. Rate limit by IP — 3 per day, no account needed.

Frontend: On the landing page (static HTML, not Angular), add a textarea and a button. The button POSTs to /api/public/analyze. The response renders below as formatted HTML. No SPA needed. No JavaScript framework. Vanilla JS fetch call.

The flow:

1. Visitor arrives at specview.dev
2. Sees the pain-first copy
3. Sees the text box: "Paste your messy thinking"
4. Pastes their brain dump
5. Hits "Analyze" — timer starts counting
6. 30-45 seconds later, analysis appears
7. Below the analysis: "Sign up to unlock the full spec suite"
8. Visitor signs up — they already know the product works

Why this is the breakthrough:

Right now: visitor reads about Specview → leaves.
After: visitor uses Specview → sees value → signs up.

The product becomes the pitch. No copy can compete with experiencing the analysis on your own messy thinking.

What this replaces: Every landing page rewrite, every copy iteration, every "should we lead with pain or features" debate. The text box makes all of that irrelevant because the visitor experiences the product instead of reading about it.

One route. One textarea. One fetch call. One rate limiter.