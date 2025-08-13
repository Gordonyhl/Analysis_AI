"""Chat API endpoints."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llm import stream_chat_response

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    thread_title: str | None = None


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest):
    """Stream the assistant's response to a chat message using SSE."""

    async def event_generator():
        async for chunk in stream_chat_response(
            payload.message, thread_title=payload.thread_title
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

