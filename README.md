## 001 Pydantic Learning – Quick Commands

Short, copy/paste-friendly commands to get running fast. Uses `uv` for Python deps and Docker for Postgres.

### Prereqs
- Python 3.12+
- Install `uv`: `pip install uv`
- Docker Desktop (for Postgres)

### Setup Python env
```bash
cd /Users/gordonli/Documents/005_Personal_Projects/001_Pydantic_learning
uv sync
```

### Start Postgres (Docker)
```bash
docker compose up -d
docker compose ps
```

Schema is auto-applied on first startup via `./db/init/001_schema.sql` (mounted into the container). To re-apply manually:
```bash
cat db/init/001_schema.sql | docker exec -i pydantic_postgres \
  psql -U "${POSTGRES_USER:-app}" -d "${POSTGRES_DB:-pydantic_learning}"
```

Open a psql shell:
```bash
docker exec -it pydantic_postgres psql -U "${POSTGRES_USER:-app}" -d "${POSTGRES_DB:-pydantic_learning}"
```

### Env vars (DB and LLM)
Either set a single `DATABASE_URL` or the individual Postgres vars. Examples:
```bash
# Option A: single URL (recommended)
export DATABASE_URL="postgresql+asyncpg://app:password@localhost:5432/pydantic_learning"

# Option B: individual parts
export POSTGRES_USER=app POSTGRES_PASSWORD=password POSTGRES_DB=pydantic_learning \
       POSTGRES_HOST=localhost POSTGRES_PORT=5432

# LLM keys (if using llm.py)
export OPENAI_API_KEY=sk-...   # if switching to OpenAI
export GOOGLE_API_KEY=....     # for Gemini
```

Settings are resolved by `settings.py` in this order: env vars > `.env` > `.env.postgres` > defaults.

### Run the FastAPI app (file validation API)
```bash
uv run uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Quick test of the `/upload` endpoint:
```bash
curl -F "file=@/path/to/data.csv" http://127.0.0.1:8000/upload | jq .
```

### Run tests
```bash
uv run pytest -q
```

### Chat CLI (persists to Postgres)
```bash
uv run python llm.py
```
Type messages; quit with `q` or `quit`. History is stored in `threads/messages` tables.

### Common Docker cleanup
```bash
docker compose down
docker volume ls | grep pydantic | awk '{print $2}' | xargs -I{} docker volume rm {}
```

### Notes
- Postgres defaults in `docker-compose.yml`: user `app`, password `password`, db `pydantic_learning` (override via env).
- The schema file is idempotent; safe to re-run.
- The app expects UTF-8 encoded CSV/TSV/TXT inputs.


