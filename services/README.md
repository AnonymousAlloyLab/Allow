# Application service boundaries

`backend/` remains the Spring authority, document store coordinator and Java
worker owner. `frontend/` remains the React workbench. `retrieval/` contains the
existing parser-routed document/retrieval libraries and the tested `allow_ai`
LangGraph library; these stable paths remain compatible with recorded evidence.

`services/ai/` contains the new application bridge, IPC protocol and deployment
runtime checks. It is a private child of Spring, with no public listening port,
SQL client or independent document authority. See
[AI integration](../docs/ai-system-integration.md) for operation and limits.

New integration code belongs with its owning service. Historical snapshots under
`gates/` and `closure/` are evidence, not active implementations.
