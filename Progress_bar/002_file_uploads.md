## File uploads: from saving to being used in chat

This doc outlines a simple, incremental plan to make uploaded files useful to the chat assistant. Today, uploads are saved to `uploads/` by `POST /upload` and not used by the chat. The goal is to associate uploaded files with conversations and surface their contents to the model during responses.

### Current state (baseline)
- Frontend: `static/js/app.js` posts `FormData` to `POST /upload` and shows a system message when done.
- Backend: `app.py:/upload` writes the file to `uploads/` and returns JSON. No parsing, no indexing, no link to a conversation.

### Target (MVP)
- When a file is uploaded, store a small metadata record in DB and optionally extract plain text.
- Associate the upload with a conversation (by thread title or id).
- At chat time, load recent messages plus relevant file text and pass that to the model.

### Design principles
- Keep it simple and incremental.
- Prefer thread-scoped association (each file linked to a single thread) to avoid global context bloat.
- Avoid heavy dependencies initially. Start with PDFs and text; expand later.

---

## Step 1 — Schema additions

Add a new table `thread_files` to record uploaded files and optional extracted text.

Suggested SQL to append to `db/init/001_schema.sql`:

```sql
-- Files attached to a thread
CREATE TABLE IF NOT EXISTS thread_files (
  id UUID PRIMARY KEY,
  thread_id UUID NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  stored_path TEXT NOT NULL,
  mime_type TEXT,
  text_excerpt TEXT,          -- optional: short excerpt for previews/search
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Optional: full extracted text in a separate table to keep rows small
CREATE TABLE IF NOT EXISTS thread_file_blobs (
  file_id UUID PRIMARY KEY REFERENCES thread_files(id) ON DELETE CASCADE,
  full_text TEXT
);
```

Minimal approach: only `thread_files` with `stored_path`, skip `thread_file_blobs` until needed.

---

## Step 2 — Storage helpers

Add simple helpers in `storage.py`:

```python
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import text

async def insert_thread_file(thread_id: uuid.UUID, filename: str, stored_path: str, mime_type: Optional[str] = None, text_excerpt: Optional[str] = None) -> uuid.UUID:
    engine = get_async_engine()
    file_id = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("""
            INSERT INTO thread_files (id, thread_id, filename, stored_path, mime_type, text_excerpt)
            VALUES (:id, :thread_id, :filename, :stored_path, :mime_type, :text_excerpt)
            """),
            {
                "id": str(file_id),
                "thread_id": str(thread_id),
                "filename": filename,
                "stored_path": stored_path,
                "mime_type": mime_type,
                "text_excerpt": text_excerpt,
            },
        )
    return file_id

async def get_files_for_thread(thread_id: uuid.UUID) -> List[Dict[str, Any]]:
    engine = get_async_engine()
    async with engine.connect() as conn:
        res = await conn.execute(
            text("""
            SELECT id, filename, stored_path, mime_type, text_excerpt, created_at
            FROM thread_files
            WHERE thread_id = :thread_id
            ORDER BY created_at DESC
            """),
            {"thread_id": str(thread_id)},
        )
        return [
            {
                "id": row[0],
                "filename": row[1],
                "stored_path": row[2],
                "mime_type": row[3],
                "text_excerpt": row[4],
                "created_at": row[5],
            }
            for row in res.fetchall()
        ]
```

Optional later: `insert_full_text(file_id, full_text)` and `get_full_text(file_id)`.

---

## Step 3 — Upload endpoint: associate with a thread and (optionally) extract text

Extend `POST /upload` to accept an optional `thread_title` (or `thread_id`). The simplest path uses `thread_title` to avoid exposing UUIDs to the client.

Protocol (frontend):
- Keep sending `FormData`. Add a JSON field `thread_title` to the same request if present in the UI.

Handler sketch (server):

```python
from fastapi import Form
from storage import get_or_create_thread_by_title, insert_thread_file

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), thread_title: str | None = Form(None)):
    # 1) Save file to uploads/
    # 2) Resolve thread_id via thread_title (or use default thread)
    # 3) Optionally extract text (lightweight for MVP)
    # 4) Insert metadata row into thread_files
    # 5) Return JSON including file_id and thread info
```

Lightweight text extraction options (choose one or skip for MVP):
- Plain text: read bytes; if `< 2MB` and UTF-8 decodable, store as excerpt.
- PDFs: use `pypdf` (pure Python) to extract text.
- DOCX: use `python-docx`.

Example excerpt logic (pseudo):

```python
def extract_excerpt(bytes_data: bytes, mime_type: str, max_chars: int = 2000) -> str | None:
    try:
        if mime_type.startswith("text/"):
            text = bytes_data.decode("utf-8", errors="ignore")
            return text[:max_chars]
        if mime_type == "application/pdf":
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(bytes_data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text[:max_chars]
        # Add more types gradually
    except Exception:
        return None
    return None
```

Keep dependencies minimal; gate advanced extraction behind feature flags later.

---

## Step 4 — Use file context during chat

Where: `llm.stream_chat_response` before invoking the agent.

Flow:
1) Resolve `thread_id` (already done today).
2) Load files for the thread via `get_files_for_thread(thread_id)`.
3) Build a compact context string: filenames + short excerpts.
4) Pass as part of the model context (e.g., prepend to system prompt or include as the first user/tool message).

Simple injection example:

```python
files = await get_files_for_thread(thread_id)
if files:
    file_ctx_lines = []
    for f in files[:3]:  # cap for token safety
        if f.get("text_excerpt"):
            file_ctx_lines.append(f"[{f['filename']}]\n{f['text_excerpt']}")
    file_context_block = "\n\n".join(file_ctx_lines)
    if file_context_block:
        system_prefix = (
            "You have access to the following user-provided files. "
            "Use them to answer questions if relevant.\n\n" + file_context_block
        )
        # Option A: prepend to the existing system prompt
        agent_with_files = Agent(
            model=agent.model,
            system_prompt=system_prefix + "\n\n" + agent.system_prompt,
            model_settings=agent.model_settings,
        )
        # Then call agent_with_files instead of agent
```

Notes:
- Keep the context small to avoid high token usage.
- Later, switch to embeddings-based retrieval per query.

---

## Step 5 — Frontend tweaks (optional for MVP)

- Include `thread_title` in the upload request when a title is present in the UI:

```javascript
const formData = new FormData();
formData.append('file', this.selectedFile);
const title = this.threadTitleInput.value.trim();
if (title) formData.append('thread_title', title);
```

- After success, you already show a system message. Optionally list attached files near the input.

---

## Step 6 — Later improvements (when needed)

- Full-text storage in `thread_file_blobs` and chunking.
- Embeddings and vector search (RAG) per question.
- File type support matrix (CSV → dataframe summaries, images → OCR, etc.).
- Background workers for heavy extraction; async task queue.
- Per-file privacy and per-thread permissions.

---

## Testing checklist

- Upload a small `.txt` and `.pdf`; verify DB rows and that excerpts appear in responses when relevant.
- Verify tokens do not explode when multiple files are attached (cap excerpts).
- Ensure deletion of a thread cascades to its files.
- Ensure non-UTF8 input does not crash extraction.

---

## Rollout plan

1) Add schema and storage helpers.
2) Extend `/upload` to accept `thread_title` and insert metadata.
3) Inject small file context block in `llm.stream_chat_response`.
4) Ship MVP; then iterate with better extraction and retrieval.


