# 🔍 Analysis: Michi Demo

**Purpose**: Evidence-based problem identification driving the [Epic](./epic.md).

**Date**: 2026-03-30

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH | 4 |
| MEDIUM | 3 |

---

## The Core Problem

Chat UIs are a bottleneck. Think of it like forcing users through a tiny dialog box when they need a full canvas.

The back-and-forth bubble format breaks flow, drops context between messages, and positions AI as something you query rather than something you work with. It's like designing a photo editor where every action requires typing a request and waiting for a response.

Here's the thing: the AI isn't the limitation. The same model that loses the thread after 50 chat messages can nail it when you give it a proper document and clear direction. The interface is the constraint, not the capability.

Documentation trails behind implementation in every software organization. Specs are written, then forgotten. Code diverges. Intent becomes archaeology. When someone new joins a project, they reverse-engineer purpose from behavior rather than reading authoritative source documents. This creates a compounding debt where the gap between "what we meant to build" and "what exists" grows wider with every sprint.
Consider: Nobody codes via chat bubbles. The entire history of developer tools is about giving people proper workspaces for the artifacts they produce—text editors evolved from punch cards to vi to VS Code, each iteration optimizing for the actual work of writing and manipulating text. IDEs emerged because developers needed more than just editing; they needed syntax highlighting, autocomplete, debugging, and refactoring tools all in one place. Version control systems like Git transformed how teams collaborate, making every change trackable, reversible, and mergeable. Diff viewers let you see exactly what changed between versions, line by line. These tools succeeded because they understood what developers actually produce: files, commits, branches, releases—tangible artifacts with clear boundaries.

Yet we've accepted chat as the primary interface for AI-assisted work, forcing users to copy-paste thousands of times to produce a coherent document. Ask Claude to write a technical spec, and you get a response in a chat bubble. Want to refine section 3? Copy it out, paste it into a new message, explain what you want changed, get a response, copy that back. Need to iterate on the introduction while keeping the conclusion intact? More copying, more pasting, more context lost between messages. A single document might require dozens of these round-trips, each one a friction point where meaning gets lost and frustration builds.

This is like asking developers to write code by describing it in emails and copy-pasting responses into their editor. Imagine: "Dear AI, please write a function that sorts an array." Response arrives. Copy. Paste into file. "Now modify it to handle null values." Copy the function back out. Paste into new email. Wait for response. Copy. Paste. No syntax highlighting during this process. No ability to undo. No way to see the history of changes. No one would accept this workflow for code—so why do we accept it for every other kind of structured document that AI helps us create?

---

## Symptoms

Users experience:

- Copy-pasting content between chat windows and actual work documents repeatedly
- Losing context when conversations grow long or span multiple sessions
- Specs that exist but are never read because they're out of date
- Code reviews that focus on implementation correctness without reference to original intent
- New team members asking "why was it built this way?" with no authoritative answer
- AI conversations that forget earlier decisions and contradict themselves
- Technical and non-technical stakeholders unable to collaborate on the same artifact
- Documentation written once, then abandoned as a "nice to have"
- Intent scattered across Slack threads, meeting notes, and partial specs
- Difficulty reproducing why a decision was made three months ago

---

## Issue Breakdown

### Critical Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Chat interface fragments complex work into disconnected exchanges | Users copy-paste content 10,000+ times when producing long-form documents via chat | Task 1 |
| Specs are passive artifacts that drift from implementation | Industry-wide pattern: docs written → forgotten → code diverges → docs become fiction | Task 2 |
| Intent is ephemeral and non-actionable | Decisions live in chat logs, meeting notes, heads—not in systems that can act on them | Task 3 |

### High Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| LLM capabilities constrained by conversational interface | Same model performs differently with structured input vs. chat fragments | Task 4 |
| No workspace designed for document-as-artifact production | Developer tools evolved from chat → editors → IDEs; AI tools stuck at chat | Task 5 |
| Spec-to-code interpretation quality varies wildly | Without enforcement (tests, contracts, static analysis), AI-generated code quality unpredictable | Task 6 |
| Technical and non-technical users need different interfaces to same truth | Product managers edit prose; engineers need architecture diagrams; both modify the same intent | Task 7 |

### Medium Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Context retrieval across large document sets is manual | Users manually reference relevant docs; no automatic RAG over spec corpus | Task 8 |
| Integration with existing dev environments requires manual export | Cursor, Claude Code, GitHub need Markdown files exported/synced manually | Task 9 |
| Quality of generated specs varies without methodology enforcement | Brain dump → useful specs requires structure (Analysis → Epic → Architecture) | Task 10 |

---

## Issues NOT Addressed (Out of Scope)

| Issue | Reason |
|-------|--------|
| Full CI/CD pipeline integration | Later phase—MVP focuses on spec editing, not deployment automation |
| Multi-user real-time collaboration | Later phase—single-user editing first |
| Custom LLM model fine-tuning | Different product concern—Spec Doc works with existing models |
| Enterprise SSO and access control | Post-validation feature |
| Mobile editing experience | Desktop-first; mobile is later optimization |

---

## Related Documents

- [Epic](./epic.md) – Scope and tasks addressing these issues
- [Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview