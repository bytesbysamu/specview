# 🎯 Epic: Side Income Strategy

## Business Value

Sam ships fast but sells slow. Five active projects compete for nights-and-weekends attention, yet none have a distribution channel that works on autopilot. The portfolio is optimized for what's fun to build, not what a solo dev with a day job can actually sell. Every week spent maintaining consumer products in saturated markets (humanize-me, Trendfy) is a week not spent on a product where the marketplace itself drives discovery. The single highest-leverage move is to stop spreading attention across five projects and concentrate on one product in a channel where distribution is built into the platform — Chrome Web Store, Shopify App Store, or an MCP server registry.

The target buyer is not a consumer scrolling TikTok. It's a professional who searches a marketplace for a solution, finds it, and pays $5–$29/mo without Sam ever knowing their name. Marketplace-native products convert strangers into customers through search ranking and reviews, not through content calendars or cold outreach. This is the only distribution model compatible with a day job, no audience, and no marketing budget.

This epic exists to force three decisions Sam has been deferring — what to kill, what to build, and where to sell it — then ship one revenue product to first paid customer. Everything after that is a different epic.

## Scope

### What This Epic Covers

- **Portfolio triage** – explicit kill/keep/passive verdict for every existing project so attention is freed before anything new starts
- **Revenue target lock** – a concrete monthly dollar target that filters product categories and effort allocation
- **Distribution channel selection** – pick ONE marketplace where discovery is platform-native (not hustle-dependent)
- **MVP product selection** – choose one product matched to the selected channel and Sam's existing stack
- **First paid customer** – ship the MVP to the marketplace and acquire the first paying user organically

### What This Epic Does NOT Cover

- ❌ **Venture-scale planning** — no fundraising, TAM analysis, or multi-year projections; re-scope if Sam quits the day job
- ❌ **Content-creator strategies** — no TikTok/IG growth playbooks; re-scope only if Sam commits to being the face
- ❌ **Multi-product portfolio** — one product, one channel, prove distribution works; diversify after first $1k/mo
- ❌ **spec-doc monetization** — it's internal tooling, not a product; re-scope only on unprompted external demand
- ❌ **OpenClaw/sam-plugin revenue** — infrastructure layer, not a product; only matters if a revenue product routes through it

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Portfolio Triage** — produce a one-line kill / keep-passive / keep-active verdict for humanize-me, Bubls, Trendfy, and spec-doc; archive killed repos, set keep-passive projects to zero-maintenance mode | None | — | 1 day | High |
| 2 | **Revenue Target & Channel Lock** — set a concrete $/mo target (e.g. $500 vs $2k vs $5k); select ONE marketplace (Chrome Web Store, Shopify App Store, or MCP registry) based on review cycle, WTP ceiling, and competition density | Task 1 | — | 1 day | High |
| 3 | **Product Selection & Validation** — identify 2–3 candidate products for the chosen marketplace; validate demand via marketplace search volume, competitor review counts, and gap analysis; commit to one | Task 2 | — | 2 days | High |
| 4 | **MVP Build & Marketplace Submission** — build the minimum shippable version of the selected product; submit to the marketplace; pass review | Task 3 | — | 5 days | High |
| 5 | **First Paid Customer** — optimize the marketplace listing (screenshots, description, keywords); monitor organic installs; reach first paying user without outbound marketing | Task 4 | — | 3 days | Low |

## Success Criteria

- ✅ Every existing project has a written kill/keep verdict — no project left in ambiguous status
- ✅ A single revenue target ($/mo) is documented and used to filter product decisions
- ✅ Exactly one marketplace is selected with a written rationale tied to distribution feasibility
- ✅ One MVP product is live and publicly listed in the chosen marketplace
- ✅ At least one customer has paid for the product through organic marketplace discovery (no cold outreach, no paid ads)

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking