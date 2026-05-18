---
name: Guide format change — TDD-only
description: Future task impl guides should contain only test cases/assertions, not implementation code. Executor figures out the code from tests.
type: feedback
originSessionId: bceb2169-d048-4238-ac89-4934b0936057
---
Change the task implementation guide (.v2.md) format: guides should NOT contain implementation code snippets.

**Instead, guides should contain:**
- Test cases and assertions (the WHAT)
- File paths and interfaces (the contract)
- Acceptance criteria expressed as tests

**The executor figures out HOW** to implement based on:
- The test specs from the guide
- The architecture doc (patterns to follow)
- The reference domain code (conventions to mirror)

**Why:** This is TDD-driven task-exec. The guide defines behavior via tests, the executor writes code that makes those tests pass. Saves tokens in the guide (no duplicate code snippets), produces better executor output (forced to read the codebase rather than copy-paste), and the tests serve as the verification step automatically.

**How to apply:** Update `server/context/prompts/task-exec-guide.md` Section 6 (Implementation Steps) to output test bodies instead of code snippets. Section 7 (Tests) becomes the primary section. Plan this change for a future session.
