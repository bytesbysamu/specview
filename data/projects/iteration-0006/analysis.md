# 🔍 Analysis: Spec Doc

**Purpose**: Evidence-based problem identification driving the [Epic](./epic.md).

**Date**: 2026-03-30

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 2 |
| HIGH | 4 |
| MEDIUM | 3 |

---

## The Core Problem

Chat-based AI interaction leaves massive capability on the table. Users are forced to work through a conversation interface that was designed for Q&A, not for producing artifacts. The result: constant copy-pasting, lost context between sessions, no version control, and documentation that perpetually lags behind reality.

The deeper issue is that chat restricts LLM potential. It's not just a UX problem — it's a capability problem. Nobody would code via chat bubbles. The entire history of developer tools is: give people a proper workspace for the artifact they're producing. Text editors. IDEs. Version control. We figured this out decades ago for code. For everything else — specs, papers, briefs, documentation — we're still in the chat dark ages.

Consider: Developers have Monaco, VS Code, Cursor. Writers have Google Docs, Notion. But for spec-driven development with AI? You're stuck in ChatGPT copying and pasting, losing context, re-explaining everything.

---

## Symptoms

Users experience:

- Copy-pasting between chat and their actual documents thousands of times
- Re-explaining context to AI at the start of every session
- Documentation that is always out of sync with code
- No single source of truth for product intent
- Inability to enforce specs during code review
- Inconsistent prompts leading to inconsistent outputs
- Non-technical stakeholders locked out of the development process
- Chat history that is unsearchable and unactionable

---

## Issue Breakdown

### Critical Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Chat interface destroys context | Users re-explain everything each session | Task 1: Document-first editor |
| No spec-to-code enforcement | PRs reviewed for code correctness only, not spec compliance | Task 4: Agent Integration |

### High Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Copy-paste workflow | "You copy paste 10000 times from chat UI" | Task 1: Document-first editor |
| Docs lag behind code | Documentation always outdated | Task 2: AI Text Operations |
| Non-technical people excluded | Can't participate in natural language development | Task 1: Document-first editor |
| Inconsistent AI outputs | Different prompts each time | Task 3: Spec Bootstrap |

### Medium Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| No git-native workflow | Specs not versioned with code | Task 5: Git Integration |
| No RAG on documentation | Context not retrievable | Future: Vector DB |
| Manual compliance checking | Hard to comply with rules | Task 4: Agent Integration |

---

## Issues NOT Addressed (Out of Scope)

| Issue | Reason |
|-------|--------|
| Team collaboration | Single user MVP first |
| Cloud sync | Local-first approach |
| Custom templates | Built-in templates only for MVP |
| Full IDE replacement | Focused on specs, not general coding |

---

## Related Documents

- [🎯 Epic](./epic.md) – Scope and tasks addressing these issues
- [🏗️ Architecture](./architecture.md) – System design
- [📅 Timeline](./timeline.md) – Status tracking
- [📋 Spec Index](./spec-index.md) – Document overview
