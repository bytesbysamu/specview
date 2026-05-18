---
name: Always use CHAIN_PROVIDER=cli for specview
description: specview local setup always uses CHAIN_PROVIDER=cli, never the Anthropic SDK directly
type: feedback
---

Always use `CHAIN_PROVIDER: cli` for specview (and spec-doc projects generally). Never switch to `CHAIN_PROVIDER: claude` with an API key.

**Why:** The Claude CLI uses the local `~/.claude` credentials and doesn't hit Anthropic SDK rate limits. Direct SDK calls with OAuth tokens (`sk-ant-oat01-`) get rate-limited when making multiple sequential API calls (e.g. the 3-step bootstrap chain).

**How to apply:** The `docker-compose.override.yml` for specview should always have:
```yaml
api:
  environment:
    CHAIN_PROVIDER: cli
  volumes:
    - /Users/sam/.claude:/home/appuser/.claude
```
Never put `ANTHROPIC_API_KEY` or `CHAIN_PROVIDER: claude` in the override. If the SDK provider ever gets set, revert it.
