from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from typing import List, Literal
from llm import agent

app = FastAPI()

# define a model for each role and their contents
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
# request model accepts user request and store in history
class ChatRequest(BaseModel):
    user_request: str
    history: List[ChatMessage] = []
@app.post("/chat")
async def chat(request: ChatRequest):
    # convert pydantic model into dictionary
    msg_history = [message.model_dump() for message in request.history]

    async def streaming_response_generator():
        async with agent.run_stream(request.user_request, message_history=msg_history) as result:
            async for message in result.stream_text():
                yield message

    return StreamingResponse(streaming_response_generator(), media_type="text/plain")

# testing if the FastAPI works
@app.get("/")
async def root():
    return {"message": "Hello World"}