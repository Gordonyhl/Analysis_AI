from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from typing import List, Literal
from llm import agent
from pydantic_core import to_jsonable_python
import json
from fastapi.middleware.cors import CORSMiddleware

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
        # First, yield the text chunks for the streaming response
        async with agent.run_stream(request.user_request, message_history=msg_history) as result:
            async for message in result.stream_text():
                yield message

            # After streaming, get the final list of messages (final messages is a list)
            final_messages = result.all_messages()
            # Convert to a JSON-serializable format
            py_obj = to_jsonable_python(final_messages)
            json_str = json.dumps(py_obj, ensure_ascii=False, indent=2)

            # Yield a separator and the final JSON history
            # The frontend will need to know to look for this separator
            yield json_str

    # We now return a streaming response with a multipart content type
    return StreamingResponse(streaming_response_generator(), media_type='text/event-stream')

# testing if the FastAPI works
@app.get("/")
async def root():
    return {"message": "Hello World"}