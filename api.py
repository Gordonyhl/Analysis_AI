"""Chat API endpoints."""

import json
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llm import stream_chat_response
from storage import get_all_threads, export_thread

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    thread_title: str | None = None


class Thread(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime


@router.get("/api/threads", response_model=List[Thread])
async def list_threads():
    """List all conversation threads."""
    return await get_all_threads()


@router.get("/api/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: uuid.UUID):
    """Return thread metadata and messages for a given thread id."""
    data = await export_thread(thread_id)

    # Normalize message content to strings for the frontend
    normalized_messages = []
    for msg in data.get("messages", []):
        content = msg.get("content")
        if isinstance(content, str):
            content_str = content
        else:
            # Ensure non-string JSON content is represented as text
            content_str = json.dumps(content, ensure_ascii=False)
        normalized_messages.append(
            {
                "idx": msg.get("idx"),
                "role": msg.get("role"),
                "content": content_str,
                "created_at": msg.get("created_at"),
            }
        )

    return {"thread": data.get("thread"), "messages": normalized_messages}


# chat stream endpoint, used by app.py for main chat interface
@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest):
    """Stream the assistant's response to a chat message using SSE."""

    async def event_generator():
        try:
            async for chunk in stream_chat_response(
                payload.message, thread_title=payload.thread_title
            ):
                # SSE spec: multi-line payloads must be sent as multiple data: lines
                # Split by universal newlines to preserve paragraph breaks
                for line in chunk.splitlines():
                    yield f"data: {line}\n"
                # End of one SSE event
                yield "\n"
            # Signal completion
            yield "data: [DONE]\n\n"
        except Exception as e:
            # Log the exception for debugging
            print(f"An error occurred during streaming: {e}")
            # Send an error message to the client
            yield f"data: [ERROR] An unexpected error occurred on the server.\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

