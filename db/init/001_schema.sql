-- Schema for conversational threads and messages
-- Auto-runs on container startup, safe to re-run with IF NOT EXISTS guards

-- Conversation threads
CREATE TABLE IF NOT EXISTS threads (
    id UUID PRIMARY KEY,                         -- Thread identifier
    title TEXT,                                  -- Optional title
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()-- Creation timestamp
);

-- Messages within threads
CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,                    -- Message ID
    thread_id UUID NOT NULL REFERENCES threads(id), -- Parent thread
    idx INTEGER NOT NULL,                        -- Order within thread
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')), -- Message role
    content JSONB,                               -- Message payload
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()-- Creation timestamp
);

-- Index for ordered reads by thread
CREATE INDEX IF NOT EXISTS messages_thread_id_idx_idx ON messages (thread_id, idx);

-- Optional: Enforce unique idx per thread
-- ALTER TABLE messages ADD CONSTRAINT messages_unique_thread_idx UNIQUE (thread_id, idx);


