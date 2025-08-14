"""Chat API endpoints."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llm import stream_chat_response

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    thread_title: str | None = None

# chat stream endpoint, used by app.py for main chat interface
@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest):
    """Stream the assistant's response to a chat message using SSE."""

    async def event_generator():
        try:
            async for chunk in stream_chat_response(
                payload.message, thread_title=payload.thread_title
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            # Log the exception for debugging
            print(f"An error occurred during streaming: {e}")
            # Send an error message to the client
            yield f"data: [ERROR] An unexpected error occurred on the server.\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

