## Product Roadmap: RNA-seq Analysis Platform

Short, practical phases to build an end-to-end prototype. Each phase has a clear goal and a milestone before you move on.

### Phase 1 — Foundation: FastAPI Basics
- **Goal**: Get a simple web server running with basic endpoints.
- **Tasks**:
  - Set up the development environment (Python, FastAPI, Uvicorn).
  - Create a minimal project structure.
  - Run a "Hello, World" FastAPI server.
  - Define initial Pydantic models:
    - RNA‑seq count table (simple structure)
    - User session model
  - Add a single file‑upload endpoint (CSV only):
    - Validate content type and required columns
    - Return clear success/error responses
- **Milestone**: Upload a CSV via API and receive a validated response.

### Phase 2 — Persistence: PostgreSQL Integration
- **Goal**: Store and retrieve data reliably.
- **Tasks**:
  - Install PostgreSQL locally and create basic tables: `users`, `sessions`, `uploaded_files`.
  - Use SQLAlchemy Core for ORM models aligned with Pydantic schemas for now.
  - Endpoints to save/retrieve session data.
  - Enhance upload flow:
    - Persist file metadata
    - Store small files in the DB (to start)
    - Endpoint to list previous uploads
- **Milestone**: Uploaded files and metadata persist in the database and are queryable.

### Phase 3 — R Integration: First Analysis
- **Goal**: Execute a simple R script from Python and return results.
- **Tasks**:
  - Start with `subprocess` to call R.
  - Write a simple R script that reads CSV and outputs basic stats.
  - Parse R output back into Python.
  - Add a FastAPI endpoint to trigger the analysis.
  - Gracefully handle R errors with meaningful messages.
- **Milestone**: Upload data → trigger R analysis → receive results.

### Phase 4 — Frontend + WebSocket
- **Goal**: Simple UI with real‑time updates.
- **Tasks**:
  - Basic HTML frontend with an upload form and results area.
  - Serve static files from FastAPI.
  - Add a WebSocket endpoint to stream progress during R runs.
  - Display live updates in the browser.
- **Milestone**: Upload → save to DB → trigger R → live progress → results shown in UI.

### Phase 5 — AI Basics: Conversational Layer
- **Goal**: Add a minimal LLM‑powered chat about uploaded data.
- **Tasks**:
  - Integrate a basic LLM (OpenAI API or local model).
  - Create a chat endpoint; store conversation history in the DB.
  - Provide the AI with analysis results for context.
  - Generate concise summaries of RNA‑seq outputs; stream via WebSocket.
  - Simple agent behavior: answer questions and suggest which analysis to run.
- **Milestone**: AI can discuss your data and propose next analyses.

### Phase 6 — Enhanced Analysis & Agent Orchestration
- **Goal**: Multiple specialized agents collaborating on analysis.
- **Tasks**:
  - Create specialized agents: data validation, analysis planning, results interpretation.
  - Introduce LangGraph for orchestration with simple workflows/decision trees.
  - Expand R script library (e.g., DESeq2, basic plots) with dynamic parameters.
- **Milestone**: Agents coordinate to validate, plan, and interpret analyses.

### Phase 7 — Advanced Features & Polish
- **Goal**: Rich visualization and a production‑ready feel.
- **Tasks**:
  - Upgrade frontend to React + Plotly; enable interactive plots from R outputs.
  - Allow plot customization via natural language prompts.
  - Improve UX; integrate external knowledge (e.g., PubMed) for context.
  - Add hypothesis generation and deeper reasoning chains.
  - Containerize the R environment with Docker for reproducibility.
- **Milestone**: Full‑featured prototype ready to publish.

### Guiding Principles
- **Start simple**: Each phase should work end‑to‑end before moving on.
- **Test frequently**: Verify each component before adding complexity.
- **Leverage mature tools**: Prefer FastAPI, SQLAlchemy, etc., over custom builds.
- **Focus**: Master each technology in isolation before composing them.

### Start Here (First Steps)
1. Run a FastAPI "Hello, World" server.
2. Add a simple CSV upload endpoint and validate it with a small file.
3. Move to Phase 2 only when Phase 1 is solid and tested.