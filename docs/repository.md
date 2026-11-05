# Repository guide

Active application code is separated by responsibility:

- `backend/`: Spring API, authority, typed model logic and sandboxed Java workers.
- `frontend/`: React workbench and draft/assistant state machines.
- `services/ai/`: private Spring-to-LangGraph process bridge, accounting adapter
  and isolated dependency verification. Tests live in `services/ai/tests/`.
- `retrieval/`: compatible Python document, retrieval and LangGraph libraries.
- `deploy/`: Windows/IIS and Linux/WSL operator scripts and tests.
- `scripts/`: reproducible builds, package creation and acceptance commands.
- `spec/` and `formal/`: normative JSON contracts and finite Lean models.
- `docs/`: current operator/developer documentation, indexed by [README](README.md).

`gates/`, `reviews/` and `closure/` retain historical evidence at its original
paths. Those directories contain large frozen snapshots; they are not a second
source tree and should not be edited during routine implementation. Historical
`dist/` packages remain in place because existing reports and operator procedures
refer to them. This change does not rewrite Git history or claim to remove its
previous binary objects.

New generated distribution archives belong in ignored `artifacts/releases/`.
Commit a small release manifest with the archive name, checksum, input evidence
and acceptance limitations. Do not commit local runtimes, virtual environments,
tokens, provider keys, dispatch journals, database dumps or new build caches.
The accidentally tracked root Vitest cache and empty JVM replay log are removed
from the Git index while their local files are retained.

Build and test the normal application with `python3 scripts/build.py`. Additional
AI tests and package instructions are in [AI integration](ai-system-integration.md).
All PostgreSQL operations continue through SQLeanParser; neither the AI bridge
nor a LangGraph checkpoint adapter introduces a direct SQL connection.
