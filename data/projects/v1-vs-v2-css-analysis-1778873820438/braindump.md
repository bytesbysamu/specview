# V1 vs V2 Rendered CSS Analysis (2026-05-15)

### Card-level comparison (computed styles from Playwright)

| Property | V1 | V2 | Issue |
|----------|----|----|-------|
| item.padding | 20px 24px | 12px 8px | V2 cards cramped — less breathing room |
| item.margin | 0px | 0px -8px | V2 bleeds edges with negative margins |
| item.borderBottom | none | 1px solid #DFDFDF | V2 adds hairline separators between cards (playground style) |
| title fallback font | Playfair Display, serif | Playfair Display, Georgia, serif | Minor — different fallback chain |
| card width | 282px | 330px | V2 columns are wider due to different grid sizing |

### Root cause
V2's `project-grid.component.css` has its own `.file-item` styles extracted from the design playground. These override the global `styles.css` definitions. The playground used tight padding (12px 8px) and hairline borders — designed for a dense component showcase. V1's global styles use 20px 24px padding and no inter-card borders — designed for comfortable reading.

### HTML comparison
The rendered HTML is structurally identical — same classes (.file-item, .file-item-title, .file-item-teaser, .file-item-meta), same data-test attributes, same section-group structure. The visual difference is purely CSS specificity: component-scoped styles (V2) override global styles (V1).

### V3 direction
- Keep V1's card padding (20px 24px) and no inter-card borders
- Keep V1's grid column sizing (282px cards)
- The fix: remove .file-item overrides from project-grid.component.css and let the global styles.css handle card styling
- Alternatively: empty out all V2 component CSS files and rely entirely on global styles.css (since the HTML uses the same classes)

### What the user wants
- V1's grid/overview layout and spacing (spacious, reader-friendly)
- V2's masthead (current version is good)
- V2's detail/expanded panel (decomposed reader-panel + sidebar-v2 components)
- V2's component architecture (5 sub-components) but with V1's visual rendering
