# Jaavis Architecture: AI Evolution Roadmap

**Status**: Planning / Future KIV
**System**: Jaavis Core (Python)

## The Vision
Transform Jaavis from a static CLI Orchestrator into an **Agentic Developer Partner**.
Instead of just indexing files, Jaavis will actively *read, understand, and generate* code based on the One-Army Library.

---

## Phase 1: The "RAG" Brain (Retrieval Augmented Generation)
**Goal**: Jaavis can answer questions using YOUR specific library pattern.

*   **Logic**:
    1.  User: `./jaavis ask "How do I do auth?"`
    2.  Jaavis: key-value searches `library/` for "auth".
    3.  Jaavis: Sends found markdown content + User User Query to LLM (Gemini/DeepSeek API).
    4.  Result: "Based on your `laravel-gold-standard` doc, here is the auth code..."
*   **Tech Stack**: `openai` (python lib), `faiss` (local vector store).

## Phase 2: The "MCP" Server (Model Context Protocol)
**Goal**: Connect Jaavis to IDEs (Cursor/Windsurf) natively.

*   **Logic**:
    1.  Jaavis exposes a local server (e.g., `localhost:3000`).
    2.  Cursor connects to Jaavis via MCP.
    3.  User (in Cursor): "@Jaavis, scaffold a new feature."
    4.  Result: Cursor reads the latest templates from Jaavis directly, without you copy-pasting.
*   **Tech Stack**: `mcp-sdk-python`, `fastapi`.

## Phase 3: The "Sentient" Loop
**Goal**: Jaavis maintains context across a session.

*   **Logic**:
    1.  User runs `./jaavis chat`.
    2.  Session starts (Memory active).
    3.  User: "Let's work on the payment module." (Jaavis loads payment docs).
    4.  User: "Generate the migration." (Jaavis knows it's for payment).
*   **Tech Stack**: `langchain`, `faiss`, `sqlite` (for chat history).

---

## Decision Log
*   **2026-02-05**: Decision made to keep Jaavis as a robust CLI first. AI features are KIV until the Knowledge Base (`library/`) is sufficiently populated.
