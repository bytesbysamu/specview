"""
mock_server.py — in-memory mock on port 3102.
One consumer: Angular frontend during Task 4 contract validation.
Replace with real Flask routes in Tasks 2 and 3.
"""
import os
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["http://localhost:4201"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _make_id(name: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    return f"{slug}-{ts}"


def _label(filename: str) -> str:
    return filename.removesuffix(".md").replace("-", " ").title()


# ── in-memory stores (reset on restart — intentional) ─────────────────────────

_PROJECTS: dict = {
    "spec-doc-1704067200000": {
        "id": "spec-doc-1704067200000",
        "name": "Spec Doc",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "files": {
            "analysis.md": "# Analysis\n\nSpec Doc solves the gap between AI chat and structured specs.",
            "epic.md": "# Epic\n\n## Goal\nShip a document-first AI editor.\n\n## MVP\nBootstrap → Edit → Save.",
            "architecture.md": "# Architecture\n\n## Stack\n- Frontend: Angular 19\n- Backend: Express + Flask",
        },
    },
    "humanize-me-1704153600000": {
        "id": "humanize-me-1704153600000",
        "name": "Humanize Me",
        "createdAt": "2024-01-02T00:00:00.000Z",
        "files": {
            "analysis.md": "# Analysis\n\nAI-generated text is detectable. Users need undetectable rewrites.",
            "epic.md": "# Epic\n\n## Goal\n$1K MRR in 30 days.\n\n## MVP\nSingle-pass humanize endpoint.",
        },
    },
    "trendfy-1704240000000": {
        "id": "trendfy-1704240000000",
        "name": "Trendfy",
        "createdAt": "2024-01-03T00:00:00.000Z",
        "files": {
            "analysis.md": "# Analysis\n\nFashion brands need affordable product photography.",
            "architecture.md": "# Architecture\n\n## Stack\n- Angular 19 + Flask + Replicate LoRA",
        },
    },
}

_CONTEXT: dict[str, str] = {
    "builder": "# Builder Profile\n\nFull-stack developer building SaaS products fast.",
    "principles": "# Principles\n\n- Ship fast, validate, iterate\n- Claude IS the algorithm",
    "codebase": "",
    "references": "",
}

_CONTEXT_KEYS = frozenset(_CONTEXT)


# ── health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return jsonify({"status": "ok"})


# ── projects ──────────────────────────────────────────────────────────────────

@app.get("/api/projects")
def list_projects():
    summaries = [
        {
            "id": p["id"],
            "name": p["name"],
            "createdAt": p["createdAt"],
            "specs": [{"filename": f, "label": _label(f)} for f in p["files"]],
        }
        for p in sorted(_PROJECTS.values(), key=lambda x: x["createdAt"], reverse=True)
    ]
    return jsonify(summaries)


@app.get("/api/projects/<project_id>")
def get_project(project_id: str):
    project = _PROJECTS.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify({
        "id": project["id"],
        "name": project["name"],
        "createdAt": project["createdAt"],
        "specs": [
            {"filename": f, "label": _label(f), "content": c}
            for f, c in project["files"].items()
        ],
    })


@app.post("/api/projects")
def create_project():
    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    project_id = _make_id(name)
    _PROJECTS[project_id] = {
        "id": project_id,
        "name": name,
        "createdAt": _now(),
        "files": {f["filename"]: f.get("content", "") for f in body.get("files", [])},
    }
    p = _PROJECTS[project_id]
    return jsonify({"id": p["id"], "name": p["name"], "createdAt": p["createdAt"]}), 201


@app.put("/api/projects/<project_id>/files/<filename>")
def update_file(project_id: str, filename: str):
    project = _PROJECTS.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    body = request.get_json(silent=True) or {}
    project["files"][filename] = body.get("content", "")
    return jsonify({"success": True})


@app.delete("/api/projects/<project_id>")
def delete_project(project_id: str):
    if project_id not in _PROJECTS:
        return jsonify({"error": "Project not found"}), 404
    del _PROJECTS[project_id]
    return jsonify({"success": True})


# ── context ───────────────────────────────────────────────────────────────────
# Flat routes match flask/modules/context/routes.py: /api/builder, /api/principles, etc.
# Flask static routes (/api/projects, /api/projects/<id>) take priority over /api/<key>.

@app.get("/api/<key>")
def get_context(key: str):
    if key not in _CONTEXT_KEYS:
        return jsonify({"error": "Not found"}), 404
    content = _CONTEXT[key]
    return jsonify({"content": content, "exists": bool(content)})


@app.put("/api/<key>")
def put_context(key: str):
    if key not in _CONTEXT_KEYS:
        return jsonify({"error": "Not found"}), 404
    body = request.get_json(silent=True) or {}
    if not isinstance(body.get("content"), str):
        return jsonify({"error": "content must be a string"}), 400
    _CONTEXT[key] = body["content"]
    return jsonify({"success": True})


# ── startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3102))
    print(f"[Mock] Spec Doc mock on http://0.0.0.0:{port}")
    print(f"[Mock] {len(_PROJECTS)} projects pre-seeded | Context: {', '.join(sorted(_CONTEXT_KEYS))}")
    app.run(host="0.0.0.0", port=port, debug=True)
