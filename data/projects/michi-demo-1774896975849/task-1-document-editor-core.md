# 🛠️ Task 1: Document Editor Core

**Purpose**: Build the foundational document workspace where users can open, edit, and preview markdown files using Monaco editor with split-view preview.

**Effort**: 3 days

**Dependencies**: None — this is the foundational task

**Parallel With**: —

**Blocks**: Task 2 (AI Operation Layer), Task 3 (Project Persistence)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Monaco editor integration with markdown syntax highlighting
- Split-view preview using marked.js
- View mode toggle (editor only / split / preview only)
- Basic file state management (content, dirty state)
- Responsive layout with resizable panes

### What's NOT Included
- File persistence — handled in Task 3
- AI operations — handled in Task 2
- Project tree/sidebar — handled in Task 3
- Authentication — out of MVP scope

---

## Prerequisites

Before starting:
- Angular 19 CLI installed (`ng version` shows 19.x)
- Node.js 20+ with npm
- Familiarity with Monaco editor API
- Understanding of Angular signals (used for state)

```bash
# Verify setup
ng version
node --version
```

---

## Implementation Steps

### Step 1: Create Angular Project

**Purpose**: Bootstrap the Angular 19 application with standalone components

```bash
ng new spec-doc --style=scss --routing=false --ssr=false
cd spec-doc
```

Configure `angular.json` for development port:

**File**: `angular.json`

```json
"serve": {
  "options": {
    "port": 4201
  }
}
```

### Step 2: Install Dependencies

**Purpose**: Add Monaco editor and markdown parser

```bash
npm install ngx-monaco-editor-v2 marked
npm install -D @types/marked
```

**File**: `angular.json`

Add Monaco assets to build configuration:

```json
"assets": [
  "src/favicon.ico",
  "src/assets",
  {
    "glob": "**/*",
    "input": "node_modules/monaco-editor",
    "output": "/assets/monaco-editor"
  }
]
```

### Step 3: Configure Monaco Module

**File**: `src/app/app.config.ts`

**Purpose**: Register Monaco editor provider for the application

```typescript
import { ApplicationConfig } from '@angular/core';
import { provideMonacoEditor } from 'ngx-monaco-editor-v2';

export const appConfig: ApplicationConfig = {
  providers: [
    provideMonacoEditor({
      baseUrl: './assets/monaco-editor/min/vs'
    })
  ]
};
```

### Step 4: Create Editor Component

**File**: `src/app/components/editor/editor.component.ts`

**Purpose**: Wrap Monaco editor with markdown configuration and two-way binding

```typescript
import { Component, input, output, signal } from '@angular/core';
import { MonacoEditorModule } from 'ngx-monaco-editor-v2';

@Component({
  selector: 'app-editor',
  standalone: true,
  imports: [MonacoEditorModule],
  template: `
    <ngx-monaco-editor
      [options]="editorOptions"
      [(ngModel)]="content"
      (ngModelChange)="onContentChange($event)">
    </ngx-monaco-editor>
  `
})
export class EditorComponent {
  content = input.required<string>();
  contentChange = output<string>();

  editorOptions = {
    theme: 'vs-dark',
    language: 'markdown',
    minimap: { enabled: false },
    wordWrap: 'on',
    lineNumbers: 'on',
    fontSize: 14
  };

  onContentChange(value: string) {
    this.contentChange.emit(value);
  }
}
```

Add FormsModule to imports for ngModel binding.

### Step 5: Create Preview Component

**File**: `src/app/components/preview/preview.component.ts`

**Purpose**: Render markdown content as HTML using marked.js

```typescript
import { Component, computed, input } from '@angular/core';
import { marked } from 'marked';
import { DomSanitizer } from '@angular/platform-browser';

@Component({
  selector: 'app-preview',
  standalone: true,
  template: `
    <div class="preview-content" [innerHTML]="renderedHtml()"></div>
  `
})
export class PreviewComponent {
  content = input.required<string>();

  constructor(private sanitizer: DomSanitizer) {
    // Configure marked for safety
    marked.setOptions({
      breaks: true,
      gfm: true
    });
  }

  renderedHtml = computed(() => {
    const html = marked.parse(this.content()) as string;
    return this.sanitizer.bypassSecurityTrustHtml(html);
  });
}
```

### Step 6: Create View Mode Toggle

**File**: `src/app/components/view-toggle/view-toggle.component.ts`

**Purpose**: IntelliJ-style toggle for editor/split/preview modes

```typescript
import { Component, input, output } from '@angular/core';

export type ViewMode = 'editor' | 'split' | 'preview';

@Component({
  selector: 'app-view-toggle',
  standalone: true,
  template: `
    <div class="view-toggle">
      @for (mode of modes; track mode.value) {
        <button 
          [class.active]="currentMode() === mode.value"
          (click)="modeChange.emit(mode.value)"
          [title]="mode.label">
          {{ mode.icon }}
        </button>
      }
    </div>
  `
})
export class ViewToggleComponent {
  currentMode = input.required<ViewMode>();
  modeChange = output<ViewMode>();

  modes = [
    { value: 'editor' as ViewMode, icon: '📝', label: 'Editor only' },
    { value: 'split' as ViewMode, icon: '📄', label: 'Split view' },
    { value: 'preview' as ViewMode, icon: '👁️', label: 'Preview only' }
  ];
}
```

### Step 7: Compose Main Layout

**File**: `src/app/app.component.ts`

**Purpose**: Assemble editor, preview, and toggle into the main workspace

```typescript
import { Component, signal } from '@angular/core';
import { EditorComponent } from './components/editor/editor.component';
import { PreviewComponent } from './components/preview/preview.component';
import { ViewToggleComponent, ViewMode } from './components/view-toggle/view-toggle.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [EditorComponent, PreviewComponent, ViewToggleComponent],
  template: `
    <div class="workspace">
      <header>
        <h1>Spec Doc</h1>
        <app-view-toggle 
          [currentMode]="viewMode()" 
          (modeChange)="viewMode.set($event)" />
      </header>
      
      <main [class]="'view-' + viewMode()">
        @if (viewMode() !== 'preview') {
          <app-editor 
            [content]="content()" 
            (contentChange)="content.set($event)" />
        }
        @if (viewMode() !== 'editor') {
          <app-preview [content]="content()" />
        }
      </main>
    </div>
  `
})
export class AppComponent {
  viewMode = signal<ViewMode>('split');
  content = signal<string>(INITIAL_CONTENT);
}

const INITIAL_CONTENT = `# Welcome to Spec Doc

Start writing your specification here.

## Features
- Monaco editor with markdown highlighting
- Live preview with marked.js
- Split view toggle
`;
```

### Step 8: Add Layout Styles

**File**: `src/app/app.component.scss`

**Purpose**: Responsive layout with CSS Grid for view modes

```scss
.workspace {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #333;
}

main {
  flex: 1;
  display: grid;
  overflow: hidden;
  
  &.view-split {
    grid-template-columns: 1fr 1fr;
  }
  
  &.view-editor {
    grid-template-columns: 1fr;
  }
  
  &.view-preview {
    grid-template-columns: 1fr;
  }
}

app-editor, app-preview {
  overflow: auto;
  height: 100%;
}
```

**File**: `src/styles.scss`

Global styles for dark theme:

```scss
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #1e1e1e;
  color: #d4d4d4;
}

.preview-content {
  padding: 1rem;
  
  h1, h2, h3 { margin: 1rem 0 0.5rem; }
  p { margin: 0.5rem 0; }
  code { background: #333; padding: 0.2rem 0.4rem; border-radius: 3px; }
  pre { background: #333; padding: 1rem; overflow-x: auto; }
}
```

---

## Verification

Run the development server:

```bash
npm start
```

Open `http://localhost:4201` in browser.

**Expected Result**:
1. Monaco editor loads with dark theme and markdown highlighting
2. Initial content displays in both editor and preview
3. Typing in editor updates preview in real-time
4. View toggle switches between editor/split/preview modes
5. No console errors

**Manual Test Checklist**:
- [ ] Editor accepts markdown input
- [ ] Preview renders headers, lists, code blocks
- [ ] Toggle buttons change layout correctly
- [ ] Content persists when switching view modes
- [ ] Editor has line numbers and word wrap

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 1 as done
2. Proceed to Task 2: AI Operation Layer (adds rewrite/expand/compress operations)
3. The editor component will be extended in Task 2 to support text selection for AI operations

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for document-as-interface
- [Epic](./epic.md) – Full task scope and MVP definition
- [Timeline](./timeline.md) – Status tracking