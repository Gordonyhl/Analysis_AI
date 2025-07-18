from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from llm import agent

app = FastAPI()

# store user request
class ChatRequest(BaseModel):
    user_msg: str

# custom function:
#  receive ans in chunks, streams message (hence yield)
async def streaming_response(user_msg: str):
    async with agent.run_stream(user_msg) as result:
        async for message in result.stream_text():
            yield message

@app.post("/chat")
async def chat(input_data: ChatRequest):
    return StreamingResponse(streaming_response(input_data.user_msg))

# testing if the FastAPI works
@app.get("/")
async def root():
    return {"message": "Hello World"}