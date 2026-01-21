Purpose
=======
This file gives short, actionable guidance for AI coding agents working in this repository so you can be immediately productive. It focuses on the repository's architecture, important developer workflows, repository-specific conventions, and concrete file examples to inspect before making changes.

Big picture
-----------
- API backend: the `api/` package implements a FastAPI-style HTTP surface (see [api/main.py](api/main.py)). Most server logic lives in `api/*_service.py` modules that follow a service pattern (e.g., `chat_service.py`, `notebook_service.py`).
- Core domain & AI: `open_notebook/` contains domain models, async database access, LangGraph workflows, and AI provisioning. Read the component CLAUDE files under `open_notebook/` for deep context (e.g., `open_notebook/CLAUDE.md`, `open_notebook/ai/CLAUDE.md`).
- Frontend: the `frontend/` folder is a Next.js + React app. UI code and hooks live under `frontend/src/` (see `frontend/src/CLAUDE.md`). The frontend talks to the backend through the `api` routes.
- Commands & prompts: `commands/` holds CLI-style command modules; `prompts/` contains prompt templates referenced by LangGraph workflows.

Key repo patterns
-----------------
- Async-first server & data flows: database, model provisioning, and graph execution are async. Do not mix sync and async without explicit bridging (`asyncio.run()` or LangGraph bridges). See `open_notebook/CLAUDE.md` and `open_notebook/database/CLAUDE.md`.
- Service pattern in `api/`: handlers are thin routers that delegate to `*_service.py` modules. When adding endpoints, add a router in `api/routers/` and implement logic in the matching service module.
- Pydantic models & repositories: Domain models are Pydantic-based under `open_notebook/domain/` and repositories live under `open_notebook/database/`. Use existing repo_* helper functions (repo_query, repo_create, repo_upsert) to keep consistency.
- LangGraph workflows: long-running or multi-step AI logic is modeled in `open_notebook/graphs/`. New workflows should be registered and documented in `open_notebook/graphs/CLAUDE.md`.

Developer workflows (commands you can run)
-----------------------------------------
- Start API locally (dev): use the project entrypoint `run_api.py` for local runs or the provided docker-compose files for containerized setups: `docker-compose.dev.yml` and `docker-compose.single.yml`.
- Run tests: use `pytest` from repo root; tests are in `tests/` and rely on the project's async test fixtures (see `tests/conftest.py`).
- Frontend dev: from `frontend/` run the standard Next.js dev script (see `frontend/package.json`).

Project-specific conventions
----------------------------
- Documentation via CLAUDE files: many directories include a `CLAUDE.md` that captures design intent and gotchas. Always read the relevant `CLAUDE.md` before editing that component (e.g., `open_notebook/CLAUDE.md`, `frontend/src/CLAUDE.md`, `api/CLAUDE.md`).
- Provider-agnostic AI model handling: model lifecycle and provider fallbacks live in `open_notebook/ai/`. Avoid hard-coding provider-specific calls; use the ModelManager or provision helpers described in `open_notebook/ai/CLAUDE.md`.
- Token & context budgeting: context assembly and token-count utilities are centralized in `open_notebook/utils/` (TokenUtils, ContextBuilder). Respect token budget helpers when modifying prompt generation.

Integration points & external dependencies
-----------------------------------------
- Database: SurrealDB / Supabase-style persistence — check `open_notebook/database/CLAUDE.md` for connection & migration behavior.
- AI providers: multiple backends supported (OpenAI, Anthropic, Google, Ollama, Mistral, etc.). Configuration and provider selection are centralized under `open_notebook/ai/`.
- Frontend ↔ API: frontend uses an Axios client and authenticated hooks. See `frontend/src/lib/api/CLAUDE.md` and `frontend/src/CLAUDE.md` for request/streaming patterns.

Concrete examples to inspect before editing
-----------------------------------------
- API entry & startup: [api/main.py](api/main.py)
- Core AI & model lifecycle: [open_notebook/ai/CLAUDE.md](open_notebook/ai/CLAUDE.md) and `open_notebook/ai/`
- LangGraph flows: [open_notebook/graphs/CLAUDE.md](open_notebook/graphs/CLAUDE.md)
- Database patterns: [open_notebook/database/CLAUDE.md](open_notebook/database/CLAUDE.md)
- Prompt templates: `prompts/` and `prompts/CLAUDE.md`

When to open a PR (practical guardrails)
----------------------------------------
- Keep changes small and focused: modify a single service/router or a single graph/workflow per PR.
- Include tests for behavioral changes: unit tests for pure logic and async tests for services that talk to repositories.
- If changing prompt templates or graph wiring, update the related `CLAUDE.md` docs to explain the reasoning.

If something is unclear
----------------------
If you can't find an authoritative `CLAUDE.md` for a component, ask for the owner, or open a draft PR and include questions in the PR description. Prefer small, reversible changes.

Next steps
----------
- For more detail, consult the component-specific CLAUDE files listed above before implementing changes.
