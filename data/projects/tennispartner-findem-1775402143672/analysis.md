# 🔍 Analysis: Tennis Partner Finder

**Purpose**: Evidence-based problem identification driving the [Epic](./epic.md).

**Date**: 2026-04-05

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 2 |
| HIGH | 3 |
| MEDIUM | 3 |

---

## The Core Problem

Finding tennis partners is frustratingly manual and unreliable. Players waste time posting in WhatsApp groups, scrolling through outdated club bulletin boards, or asking friends who may not be available or at a compatible skill level. The result: cancelled plans, mismatched games, and players who simply stop trying.

The tennis community lacks a dedicated, efficient way to connect players. General-purpose apps don't understand tennis-specific needs like skill level matching, preferred play styles, or court availability. Dating apps solved the "find compatible people nearby" problem years ago—tennis players are still stuck in the dark ages.

Consider: It's like trying to find a carpool partner by shouting into a crowded room instead of using a ride-sharing app.

---

## Symptoms

Users experience:

- Spending 30+ minutes coordinating a single match via group chats
- Games cancelled last-minute due to no confirmed partner
- Playing with mismatched skill levels (too easy or too hard)
- No visibility into who's available when they want to play
- Relying on the same 2-3 contacts, limiting variety
- Joining clubs just to access player networks, not for the amenities
- Giving up on spontaneous play due to coordination friction
- Missing out on local players they'd enjoy playing with

---

## Issue Breakdown

### Critical Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| No efficient discovery mechanism for nearby players | Players resort to generic social media, word-of-mouth | Task: Player discovery |
| High friction to coordinate matches | Multi-step process across different platforms (chat, calendar, maps) | Task: Match coordination |

### High Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Skill level mismatches ruin games | No standardized way to communicate ability; self-ratings unreliable | Task: Skill matching system |
| Availability information is scattered | Players don't know when others are free without asking individually | Task: Availability features |
| No trust signals for meeting strangers | Safety concerns when connecting with unknown players | Task: Profile verification |

### Medium Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Court booking separate from partner finding | Players must coordinate partner AND court independently | Task: Court integration |
| No record of past games or preferred partners | Relationships and history lost; must rebuild context each time | Task: Match history |
| Location preferences unclear | Players may prefer specific clubs, neighborhoods, or court types | Task: Location preferences |

---

## Issues NOT Addressed (Out of Scope)

| Issue | Reason |
|-------|--------|
| Court booking marketplace | Different product; partner finding is the core value |
| Tournament organization | Phase 2; requires established user base first |
| Coaching/lessons marketplace | Different user intent; dilutes core use case |
| Equipment buy/sell | Tangential to partner matching |
| Live scoring/statistics | Feature creep; not part of "find and connect" |

---

## Related Documents

- [Epic](./epic.md) – Scope and tasks addressing these issues
- [Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview