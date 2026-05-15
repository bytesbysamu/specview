# Unified Page V3 — Best of V1 + V2

## The goal

V3 = V1's visual rendering + V2's component architecture. One page at /v2 (eventually /) that looks exactly like V1 but is built from V2's decomposed sub-components.

## What to keep from V1

- Card padding: 20px 24px (not V2's cramped 12px 8px)
- No hairline borders between cards within a section group
- Grid column sizing: 282px cards (not V2's 330px)
- Section group spacing and separators
- Search bar with left-aligned project count
- Panel slide animation (@panelEnter) on expanded view
- Word count pipe in reader panel
- Usage meter in masthead
- The overall spacious, reader-friendly feel

## What to keep from V2

- Masthead (V2's version — user confirmed it looks good)
- 5 decomposed sub-components: ProjectGridComponent, ReaderPanelComponent, SidebarV2Component, StatusBarComponent, SectionNavComponent
- Component input/output contracts (clean data flow)
- Landing pitch component for anonymous visitors
- Design playground component (fetch-based, avoids Angular template parsing issues)
- Auth-conditional rendering (@if toggle)

## What to fix

### CSS specificity problem (root cause of all visual differences)
V2's component CSS files have their own .file-item, .expanded-sidebar, etc. styles extracted from the design playground. These override the global styles.css definitions due to Angular's component style encapsulation.

The fix: empty out all V2 component CSS files and let the global styles.css handle all styling. The HTML already uses V1's class names — the global styles will apply correctly once the component-scoped overrides are removed.

### Specific CSS overrides to remove
- project-grid.component.css — .file-item padding/margin/border overrides
- sidebar-v2.component.css — .expanded-sidebar, .sidebar-file overrides
- reader-panel.component.css — .expanded-main, .markdown-content overrides
- status-bar.component.css — .gen-status-bar overrides
- section-nav.component.css — .section-nav, .section-link overrides

## Implementation approach

1. Empty all 5 V2 component CSS files (keep the files, just clear contents)
2. Verify global styles.css renders correctly in V2 components
3. Add back only minimal scoped styles that genuinely don't exist globally
4. Screenshot compare V1 vs V2 — grid, cards, spacing should be identical
5. Keep V2's expanded panel decomposition

## Success criteria

- V2 overview/grid visually identical to V1 (same padding, card width, separators)
- V2 masthead stays as-is
- V2 expanded/detail panel uses decomposed components
- ng build passes, 155 frontend tests pass
- No regression in V1 (stays untouched at /)
