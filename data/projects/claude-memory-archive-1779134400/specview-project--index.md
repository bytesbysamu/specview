# Memory Index

- [specview local data directory](project_spec_doc_dir.md) — SPEC_DOC_DIR=data; projects at data/projects/<id>/
- [always use plugin](feedback_use_plugin.md) — route every task through agents/skills, never implement inline
- [Agent dispatch preference](feedback_agent_dispatch.md) — use specialist subagent types, not general-purpose, for exec-guide tasks
- [No direct code edits](feedback_no_direct_edits.md) — create braindump project first, never edit files directly from a verbal request
- [Braindump style](feedback_braindump_style.md) — no explicit tasks in braindumps; that's the spec pipeline's job
- [Exec summaries append-only](feedback_exec_summary_append.md) — always append new sections, never overwrite the file
- [exec-guide full procedure](feedback_exec_guide_full_procedure.md) — background agents must run ALL steps (test, review, PR, CI, merge, summary), not just tasks
- [exec-guide must complete all steps](feedback_exec_guide_full.md) — when /exec-guide is invoked, NEVER skip post-implementation steps (dev-test, dev-review, commit, PR, CI, merge, summary)
- [Specview not Spec Doc](feedback_specview_not_specdoc.md) — always use "Specview" branding, never "Spec Doc"
- [Playground is the superset](feedback_playground_superset.md) — playground includes ALL design (design system, app, landing); landing page is a curated subset extracted to pure HTML
