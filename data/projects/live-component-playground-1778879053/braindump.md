# Live Component Playground

## What this is

Replace the current static design playground (2,304 lines of hardcoded HTML loaded via DOMParser) with a live, interactive playground where every V2 sub-component renders with real services and real data. Instead of a screenshot of the app, you see the actual app components working — clicking, generating, polling, animating — all on one scrollable page.

## Why

The static playground is a design reference — useful for comparing CSS tokens and layout, but it's frozen. It can't show:
- A real project grid with your actual projects
- A status bar that updates during generation
- A sidebar where you click files and see markdown render
- AI text ops that actually call the backend
- Dark mode toggling across all components simultaneously

A live playground proves the components work. It's also the best demo for new users — they see every feature in action without navigating through the app.

## Current state

- `design-playground.component.ts` — fetches static `playground.html` via DOMParser, injects into DOM
- `landing/playground.html` (2,304 lines) — static HTML with hardcoded project names, lorem ipsum specs, fake status states
- The playground shows tokens, borders, components, animations, states, and "App vs Landing" comparison — all static

## The live playground

One Angular component (`live-playground.component.ts`) that renders every V2 sub-component with real or mock data, organized in sections:

### Section 1: Section Nav (live)
```
<app-section-nav
  [sections]="demoSections"
  [activeSection]="demoActiveSection()"
  [sectionCounts]="demoSectionCounts()"
  [pulsingSections]="demoPulsingSections()"
  [contextFileCount]="6"
  (sectionSelected)="demoActiveSection.set($event)" />
```
- Click tabs, see counts update, watch pulse animation
- Uses local demo signals, not the real project service

### Section 2: Status Bar (live, all 4 states)
```
<h3>Idle</h3>
<app-status-bar [mode]="'idle'" ... />

<h3>Active</h3>
<app-status-bar [mode]="'active'" [specGenProjectName]="'Demo Project'" [specGenStep]="'architecture'" ... />

<h3>Success</h3>
<app-status-bar [mode]="'success-flash'" ... />

<h3>Failure</h3>
<app-status-bar [mode]="'failure'" [statusFailureMsg]="'AI provider timeout'" ... />
```
- All 4 states visible simultaneously
- Active state shows real animated dots and timer

### Section 3: Project Grid (live with real data)
```
<app-project-grid
  [activeSection]="'all'"
  [filteredProjects]="realProjects()"
  [projectsBySection]="realProjectsBySection()"
  ... />
```
- Option A: Use real ProjectsService to load actual projects (requires auth)
- Option B: Use hardcoded demo projects that look real (works without auth)
- Recommended: Option B for anonymous, Option A when logged in

### Section 4: Sidebar (live)
```
<app-sidebar-v2
  [activeProject]="demoProject"
  [activeFile]="demoActiveFile()"
  [canGenerateSpecs]="true"
  [canGenerateEpicGuide]="true"
  [currentSpec]="demoSpec"
  [isBraindump]="true"
  ... />
```
- Click files, see active state change
- AI op chips visible and clickable (toggle active state)
- Generate buttons visible (disabled, just for display)

### Section 5: Reader Panel (live)
```
<app-reader-panel
  [activeProject]="demoProject"
  [currentSpec]="demoSpec"
  [parsedContent]="demoParsedMarkdown"
  [expandedTitle]="'Demo Architecture'"
  ... />
```
- Renders real markdown via marked + DOMPurify
- Shows the 2-column newspaper layout
- Diff view with sample before/after

### Section 6: Landing Pitch (live)
```
<app-landing-pitch />
```
- Already a static component — renders as-is

### Section 7: Create Modal (live)
- A button that opens the real create-project modal
- Type a name and braindump, see validation
- Generate button works (if connected to real service) or shows loading state

### Section 8: Dark Mode Toggle
- One button at the top that toggles dark mode for ALL playground sections simultaneously
- Shows every component in both light and dark themes

## Architecture

### One component, demo signals
```typescript
@Component({
  selector: 'app-live-playground',
  standalone: true,
  imports: [
    SectionNavComponent, StatusBarComponent, ProjectGridComponent,
    SidebarV2Component, ReaderPanelComponent, LandingPitchComponent,
    UsageMeterComponent
  ],
  templateUrl: './live-playground.component.html',
  styleUrl: './live-playground.component.css',
})
export class LivePlaygroundComponent {
  // Demo data — hardcoded projects, specs, sections
  demoProjects = signal<Project[]>([...DEMO_PROJECTS]);
  demoActiveSection = signal('all');
  demoActiveProject = signal<Project | null>(null);
  demoActiveFile = signal<string | null>(null);
  demoSpec = signal<Spec | null>(DEMO_SPEC);
  
  // Computed from demo data
  demoSectionCounts = computed(() => ...);
  demoProjectsBySection = computed(() => ...);
  demoFilteredProjects = computed(() => ...);
  
  // Parsed markdown for reader
  demoParsedMarkdown = computed(() => {
    const spec = this.demoSpec();
    if (!spec?.content) return '';
    return this.sanitizer.bypassSecurityTrustHtml(
      DOMPurify.sanitize(marked.parse(spec.content))
    );
  });
}
```

### Demo data constants
```typescript
const DEMO_PROJECTS: Project[] = [
  { id: 'demo-1', name: 'Authentication Flow', specs: [...], ... },
  { id: 'demo-2', name: 'Billing Integration', specs: [...], ... },
  { id: 'demo-3', name: 'API Rate Limiting', specs: [...], ... },
  // 8 projects across all 4 sections
];

const DEMO_SPEC: Spec = {
  filename: 'architecture.md',
  label: 'Architecture',
  content: '# Solution Architecture\n\n## Overview\n\nThis document describes...',
};
```

### Route
```
{ path: 'playground', component: LivePlaygroundComponent }
```
Replaces the static design playground. The old `DesignPlaygroundComponent` (DOMParser-based) can be kept at `/playground-static` as a reference or deleted.

## What this replaces
- `design-playground.component.ts` (34 lines, DOMParser fetch)
- `web-ng/public/assets/playground.html` (2,304 lines, static copy)
- `web-ng/public/assets/landing-style.css` (1,224 lines, static copy)

## What this does NOT include
- Real AI calls from the playground (too expensive for a demo page)
- Real project creation (would pollute the user's project list)
- Real Stripe checkout flow
- Editable spec content (read-only display)

## Success criteria
- Every V2 sub-component visible and interactive on one page
- Status bar shows all 4 states simultaneously
- Grid renders with demo projects in all sections
- Sidebar file nav is clickable, updates reader panel
- Dark mode toggle affects all sections
- No real API calls needed (works without auth)
- `ng build` passes, no new test failures
