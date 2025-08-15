"""Chat API endpoints."""

import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llm import stream_chat_response
from storage import get_all_threads

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

