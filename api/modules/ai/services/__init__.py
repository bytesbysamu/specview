"""ai.services — pure business logic for AI generation (no Flask imports).

Populated in Task 3 (split from modules/spec_gen/service.py, modules/task_gen/service.py).
"""

SKEPTICISM_PROMPT = (
    "Distinguish user data from domain claims. The user's own measurements, tool "
    "choices, and business decisions are legitimate input — analyze them without "
    "challenge. Claims presented as universal domain facts (industry standards, "
    "named methodologies, benchmark thresholds) without attribution should be "
    "flagged as unverified. When precise numbers are stated as domain facts rather "
    "than the user's own data, note them as unverified. When a proper-noun "
    "framework or protocol is referenced that you don't recognize, flag it as "
    "requiring verification rather than assuming it exists."
)
