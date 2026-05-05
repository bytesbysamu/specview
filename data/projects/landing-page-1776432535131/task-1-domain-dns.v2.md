The implementation guide is ready. Here's what was generated:

**Task 1: Domain + DNS** — a pure infrastructure task (no repo code changes). The guide covers:

| Section | Key Content |
|---------|-------------|
| **Context** | `.app` TLD enforces HSTS, Coolify handles SSL in Task 5 |
| **Trade-offs** | `bubls.ch` (geo-locked), `trendfy.me` subdomain (brand coupling) rejected in favor of `bubls.app` |
| **Steps** | 4 steps: register domain → create A + CNAME records → verify propagation via `dig` → update timeline |
| **Tests** | 3 bash assertions (A record resolves, CNAME resolves, VPS reachable) — no automated tests since it's external infra |
| **Commit** | Single commit: timeline status update only |
| **Critical note** | Cloudflare proxy must be OFF (grey cloud) — Coolify needs direct VPS access for Let's Encrypt HTTP-01 challenges |

The guide is waiting for write permission to save to `projects/landing-page-1776432869599/task-1-domain-dns.md`. Want me to retry the write?

---

##### Post-generation review (auto)

**Overall**: 4/5 (silver)

| Dimension | Score | Key Finding |
|-----------|-------|-------------|
| Structural completeness | 3/5 | Missing Prerequisites section — VPS IP address, registrar account access, Coolify dashboard URL are all needed before starting but not listed |
| Content routing | 4/5 | Trade-offs table (bubls.ch, trendfy.me rejected) duplicates Architecture's Design Decisions table row 8 — implementation guide should reference the Architecture decision, not re-argue it |
| Pattern application | 3/5 | No formal scope boundaries with ✅/❌ markers — steps imply scope but don't draw the line explicitly |
| Rule compliance | 4/5 | Status correctly deferred to Timeline — commit step updates timeline only (good) |
| Content quality | 4/5 | Strong: 'Cloudflare proxy must be OFF (grey cloud)' is exactly the kind of opinionated, failure-preventing callout that makes guides useful |
| Usefulness | 4/5 | Missing prerequisite info means a developer would need to context-switch to find VPS IP, registrar credentials, and Coolify access before starting |

**Top fixes**:
- Add Prerequisites section: VPS IP address (from Coolify dashboard or `dig trendfy.me`), registrar account, Coolify dashboard URL, and confirmation that no other service claims the domain
- Add Cross-references: link to Epic Task 1 detail, Architecture Component Design (Task 1), and Architecture Design Decisions (Domain row) — then add reverse link from Architecture to this implementation guide
- Add 'What's NOT Included' + 'Next Steps' sections: explicitly state this task does NOT configure Coolify or SSL (that's Task 5), and point to Task 5 as the immediate downstream consumer of the DNS output
