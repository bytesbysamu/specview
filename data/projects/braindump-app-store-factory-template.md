# spec-doc — App Store Factory: Standardised Project Template

## What

Add a "New from Template" flow to spec-doc's project creation. Templates are YAML files that pre-populate the braindump field, project name prefix, and a set of starter spec files (analysis, epic, architecture stubs). The first template is "Ionic + Capacitor mobile app" — the Bubls/Springular/Trendfy shape that ships repeatedly.

Every new app store product starts with the same bootstrap questions: RevenueCat, Supabase auth, App Store CI/CD, iOS target version, Capacitor plugins. Encoding that tribal knowledge in a template means the bootstrap output is structured and consistent from the first call.

### 1. Template format — YAML in api/resources/templates/

```yaml
# api/resources/templates/ionic-capacitor-app.yaml
id: ionic-capacitor-app
name: Ionic + Capacitor Mobile App
description: RevenueCat subscriptions, Supabase auth, App Store CI/CD
tags: [mobile, ionic, capacitor, revenue-cat]

braindump_prefix: |
  This is an Ionic + Capacitor mobile app targeting iOS 16+ and Android 12+.
  Auth: Supabase (email + Apple Sign-In).
  Payments: RevenueCat (monthly + annual tiers, free trial).
  Deployment: GitHub Actions → TestFlight → App Store Connect.

starter_files:
  - filename: analysis.md
    content_template: templates/partials/ionic-analysis.md
  - filename: architecture.md
    content_template: templates/partials/ionic-architecture.md
```

`braindump_prefix` is prepended to the user's braindump before the AI sees it. It injects the stack constraints without the user having to remember them.

### 2. GET /api/templates — list available templates

```python
# modules/templates/routes.py
@templates_bp.get("/")
def list_templates():
    templates_dir = Path(RESOURCES_DIR) / "templates"
    result = []
    for f in templates_dir.glob("*.yaml"):
        t = yaml.safe_load(f.read_text())
        result.append({"id": t["id"], "name": t["name"], "description": t["description"], "tags": t.get("tags", [])})
    return jsonify(result)
```

### 3. POST /api/ai/text/bootstrap-project — accept template_id

```python
class BootstrapProjectRequest(BaseModel):
    project_name: str
    braindump: str
    template_id: Optional[str] = None  # new field
```

In the handler (or background thread for the async version):

```python
if req.template_id:
    template = load_template(req.template_id)
    effective_braindump = template["braindump_prefix"] + "\n\n" + req.braindump
else:
    effective_braindump = req.braindump
```

Starter files are written into the project directory before the AI chain runs, so the architecture step can reference them as existing context.

### 4. Angular — template picker in new-project modal

```typescript
// new-project.component.ts
templates: Template[] = [];

ngOnInit() {
  this.templateService.list().subscribe(t => this.templates = t);
}
```

UI: a row of template cards (icon + name + description) above the braindump textarea. Selecting one sets `selectedTemplateId` and populates a "starter context" chip showing what the template adds. User can still clear it and bootstrap from scratch.

### 5. Template library (phase 2 templates)

| Template ID | Covers |
|---|---|
| `ionic-capacitor-app` | RevenueCat + Supabase + App Store CI/CD |
| `flask-angular-api` | spec-doc-api shape: Blueprint modules, openapi.yaml, DTOs, pytest |
| `next-js-saas` | Next.js 15 + Supabase + Stripe + shadcn |
| `ai-feature-module` | Chain adapter pattern, async 202+polling, prompt functions |
| `data-pipeline` | ETL shape: ingest → transform → load, idempotency keys |

Each template encodes the architecture principles relevant to that stack so the bootstrap prompt carries them automatically.

### 6. openapi.yaml additions

```yaml
/api/templates:
  get:
    summary: List available project templates
    responses:
      200:
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/components/schemas/Template'

components:
  schemas:
    Template:
      type: object
      required: [id, name, description]
      properties:
        id: { type: string }
        name: { type: string }
        description: { type: string }
        tags:
          type: array
          items: { type: string }
```

`BootstrapProjectRequest` gains `template_id: { type: string, nullable: true }`.

## Why now

Every Bubls-shape app starts with the same 20-minute conversation reconstructing the same stack decisions. A template front-loads that context so the bootstrap output arrives pre-structured. The `ionic-capacitor-app` template alone saves a revision cycle on every new app.

The 6-month plan targets 3–5 new apps. Templates multiply the value of spec-doc linearly.

## What's missing

One decision: **where do templates live in the monorepo?** Options:
- (a) `api/resources/templates/` — close to the code that loads them, backend-only concern
- (b) `docs/templates/` — visible at the repo root, easier for non-developer edits
- (c) `projects/templates/` — co-located with project braindumps, same directory structure

Option (a) is cleanest (co-located with the loader). The templates are a backend resource, not project documents.

## Explicitly out of scope

- User-created templates (saved from existing projects) — phase 3
- Template versioning (v1, v2) — not needed until templates are shared across teams
- Remote template registry — local YAML files are sufficient
- Template inheritance / composition — YAGNI
