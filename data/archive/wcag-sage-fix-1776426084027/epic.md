# WCAG Sage Accent Fix — Epic

**Purpose**: Fix 2 WCAG-AA contrast failures on chain-mode buttons.

## Task

| # | Task | Effort | Priority |
|---|------|--------|----------|
| 1 | **Darken --accent-sage tokens** | 15 min | High |

### Task 1: Darken --accent-sage tokens
Change `--accent-sage` light from `#5A7A6A` to `#4D6D5D` and dark from `#7A9A8A` to `#6D8D7D` in `src/app/styles/tokens.scss`. Run `npm run test:a11y` to verify both pairs now clear 4.5:1. One commit.

## Success Criteria
- `npm run test:a11y` passes with 0 failures
- Sage buttons visually distinguishable in both modes
