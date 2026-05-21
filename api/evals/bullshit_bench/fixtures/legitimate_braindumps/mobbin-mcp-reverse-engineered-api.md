# Mobbin MCP — Braindump

## What it is

An unofficial MCP server that gives Claude (and any MCP-compatible client) direct access to Mobbin — a design-inspiration platform with 600k+ screens from 1,100+ apps. Mobbin has no public API; the server works by reverse-engineering their internal Next.js API routes and authenticating via Supabase session cookies.

## Problem it solves

Design research on Mobbin normally requires manual browser browsing. This server lets an agent search apps, screens, and user flows by pattern/category/keyword, retrieve full-resolution screenshots (as base64 for vision models), extract dominant colors, and browse the user's saved collections — all from a chat prompt. Turns a passive reference library into an active design tool.

## Current state

Fully shipped and functional. Published to npm as `mobbin-mcp` (installable via `npx -y mobbin-mcp`). Eight tools implemented:

- `mobbin_search_apps` — search/browse apps by category + platform
- `mobbin_search_screens` — search by UI pattern, element, or keyword
- `mobbin_search_flows` — search user flows by action type
- `mobbin_quick_search` — autocomplete app name lookup
- `mobbin_popular_apps` — popular apps grouped by category
- `mobbin_list_collections` — user's saved collections
- `mobbin_get_screen_detail` — fetch screenshot as base64 with optional color extraction (via sharp)
- `mobbin_get_filters` — all available filter taxonomy (categories, patterns, elements, actions)

Auth is handled either via a CLI wizard (`npx mobbin-mcp auth` saves to `~/.mobbin-mcp/auth.json`) or a manually set `MOBBIN_AUTH_COOKIE` env var. Tokens auto-refresh via Supabase's `/auth/v1/token` endpoint before expiry.

## Key decisions already made

- **Reverse-engineered API, not official**: Mobbin is Next.js + Supabase; all calls go to `/api/content/*` routes, not Supabase RPC directly (the older approach used direct Supabase calls). Cookie-based auth, not OAuth from the server side.
- **CLI auth as primary flow**: Easier than DevTools extraction; guides user to run `copy(document.cookie)` in browser console.
- **Images via CDN conversion**: Supabase storage URLs from search results are converted to Bytescale CDN URLs, fetched, and returned as base64 — this is what lets vision models actually see the screens.
- **Color extraction is optional**: Uses `sharp`; heavyweight dependency kept isolated in `mobbin_get_screen_detail`.
- **TypeScript strict mode**, ISC license, community-contribution-friendly structure.

## Open questions

- Mobbin may change internal API routes without warning — no contract stability guarantees. The server could break silently.
- Cookie-based auth has a 1-hour TTL; refresh logic assumes the Supabase token structure stays stable.
- No support yet for web/sites search (only iOS/Android apps), though the API supports it.
- `mobbin_quick_search` returns only IDs; cross-reference requires hitting `/api/searchable-apps/{platform}` — could be slow or cached differently per platform.

## Next steps

- Monitor for API breakage; consider a canary ping tool.
- Add web/sites search as a tool variant.
- Explore flow video support (Bytescale CDN serves MP4s).
- Consider publishing a Python port via FastMCP for parity with the mcp-builder skill pattern.
