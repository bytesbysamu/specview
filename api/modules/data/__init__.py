"""modules/data — storage adapters: filesystem-backed content + git_store + db engine.

Sub-packages (db, git_store, projects, context, templates) own their own
service / repository modules. This package intentionally re-exports nothing
so each backend evolves independently.
"""
