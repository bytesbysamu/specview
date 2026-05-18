---
name: Test naming convention
description: Use present tense verbs in test names, never "should" — e.g. it('creates') not it('should create')
type: feedback
---

Test names use present tense without "should":
- `it('creates')` not `it('should create')`
- `it('reads color tokens on init')` not `it('should read color tokens on init')`
- `it('updates values when dark mode toggles')` not `it('should update values...')`

**Why:** Cleaner, more direct, reads as a specification rather than a suggestion.

**How to apply:** Every `it()` block in Jasmine/Jest tests uses present tense verb form. No "should" anywhere in test descriptions.
