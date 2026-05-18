---
name: claude CLI has no --system flag
description: The claude CLI does not support --system flag; combine system + user into one -p argument
type: feedback
---

When invoking `claude` CLI from a skill or script, `--system` is not a valid flag and will error.

**Why:** Discovered when impl-guide skill failed with `error: unknown option '--system'`, leaving an empty output file.

**How to apply:** Combine system prompt and user prompt into a single `-p` argument: `claude -p "<system content>\n\n<user prompt content>"`. Fix any skill or script that uses `--system` to use this pattern instead.
