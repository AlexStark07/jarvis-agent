# JARVIS AI - Architecture Audit Report

## 1. Current Architecture & Actually Implemented Features

### Verified Functionality
- **Task Lifecycle Management:** `src/jarvis/tasks.py` correctly implements an Enum-based state machine for tasks (`QUEUED`, `PLANNING`, `RUNNING`, `WAITING_FOR_APPROVAL`, `VERIFYING`, `SUCCEEDED`, `FAILED`, `CANCELLED`). Transitions between states are explicitly verified via `ALLOWED_TRANSITIONS` mappings.
- **Task Persistence Layer:** `src/jarvis/repository.py` implements a SQLite-backed repository. It successfully provides atomic saving of `Task` objects and their associated `ExecutionEvent`s. It includes table creations, foreign keys, and indexes mapping appropriately to models.
- **Execution Event Tracking:** Both `src/jarvis/events.py` and the `ExecutionService` in `src/jarvis/execution/service.py` construct proper event trails and link them with task state changes. The codebase correctly models events capturing transitions and metadata in JSON format.
- **Automated Testing Setup:** `tests/` contains a comprehensive set of test modules targeting core state transitions (`test_core.py`), database interactions (`test_repository.py`), and execution workflow handling (`test_execution_service.py`). Under a properly configured `PYTHONPATH`, 20 tests execute successfully and verify edge cases such as invalid status transitions.

### Missing or Untested Functionality
- **Orchestrator and Agents:** The multi-agent LangGraph orchestrator (the "Boss/Supervisor") and the 5 specialist agents mentioned in `PROJECT_MEMORY.md` are completely absent from the codebase.
- **Workers and Docker Integration:** The isolated Docker workers, designed to constrain execution environments, have not been implemented. There are no Dockerfiles or sandbox managers present.
- **API / Control Plane:** FastAPI server and web hooks are not yet constructed. There's no REST or WebSocket API to interact with the system.
- **Tool Implementations:** Real tools (search, file operations, n8n) and external dependencies (like ElevenLabs for voice) remain unimplemented.

## 2. Code Review & Problem Identification

### Missing Error Handling & Architectural Risks
- **Dependency Management:** There's no `requirements.txt`, `pyproject.toml`, or `Pipfile`. While the README dictates usage of `.venv`, there is no standardized way to set up the environment, leading to `ModuleNotFoundError` by default.
- **Config Management:** There's no support for configuration injection (e.g. `dotenv`, environment variables). The database is hardcoded to `data/jarvis.db` in the repository initializer if no path is provided.
- **Security Risks:** Since the execution workers haven't been implemented yet, there are no immediate exposed API keys or secrets in the repository. However, the lack of environment configuration implies secrets might be hardcoded as the implementation progresses.
- **Lack of Dependency Injection:** The setup tightly binds internal domains (e.g., SQLite DB initializations happening inside `TaskRepository` constructor automatically, without utilizing a migration script approach like `Alembic`).

### Identified Bugs
- **Missing Optimistic Concurrency Update:** In `src/jarvis/tasks.py`, `Task` contains a `version: int = 0` field, but this is never utilized during database updates in `TaskRepository`. The schema doesn't store this field, and `save_task_with_event` doesn't enforce atomic conditional updates based on version. This will result in race conditions (the stated `ConcurrentTaskUpdateError` in `repository.py` is present but never raised).

## 3. Prioritized Roadmap to Production

To transform this baseline into the production-ready multi-agent AI OS described in the documentation:

### Phase 1: Environment & Persistence Hardening (Immediate)
1. **Dependency Definition:** Introduce `pyproject.toml` or `requirements.txt` to lock dependencies (FastAPI, SQLite tools, LangGraph, etc.).
2. **Implement Database Migrations:** Introduce `Alembic` to manage SQLite schema changes formally, migrating away from `_initialize()` pragmas in Python code.
3. **Concurrency Fix:** Resolve the identified database versioning bug to support optimistic concurrency before integrating concurrent agents.

### Phase 2: API and Orchestration Foundations
4. **FastAPI Control Plane:** Develop the API server to allow remote/voice clients to enqueue tasks and retrieve task states/events.
5. **LangGraph Orchestrator:** Implement the Supervisor agent logic. This parent node will manage the `Task` queue and determine delegation to specific agents.

### Phase 3: Specialist Agents & Capabilities
6. **Agent Modules:** Scaffold the 5 specialist agents with explicitly defined contracts (input schema, tools, system prompts).
7. **Tool Gateway Framework:** Build the validation middleware to enforce permissions before an agent executes a tool. Implement human-in-the-loop (`WAITING_FOR_APPROVAL`) endpoints.

### Phase 4: Isolated Execution Workers
8. **Worker Containers:** Build Docker-based execution sandboxes that agents will dispatch tool tasks to (with CPU/memory bounds and no internet access by default).
9. **Observability Sync:** Integrate standard structured logging to aggregate real-time execution events without exposing private model reasoning.

## 4. Focused Fix Proposal: Optimistic Concurrency Bug

### The Issue
Currently, `ConcurrentTaskUpdateError` is defined in `repository.py` but never utilized. The `Task` object tracks `version` locally, but `TaskRepository._initialize()` does not create a `version` column, nor does `update_task()` or `save_task_with_event()` increment and check the version to prevent "lost updates" from simultaneous workers.

### The Proposed Fix
1. **Schema Update:** Update `CREATE TABLE IF NOT EXISTS tasks` to include `version INTEGER NOT NULL DEFAULT 0`.
2. **Repository Read:** Modify `get_task()` to populate the `Task.version` from the DB row.
3. **Repository Update:** Modify the `UPDATE tasks` statements to include `WHERE task_id = ? AND version = ?`, and `SET version = version + 1`.
4. **Error Handling:** If `cursor.rowcount == 0`, throw `ConcurrentTaskUpdateError("Task was updated by another process.")` instead of a generic `KeyError`.
5. **Tests:** Add a specific test in `test_repository.py` simulating two concurrent instances fetching the same task, where the second fails to save.
