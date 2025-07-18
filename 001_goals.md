### Badass checklist, each item build on top of each other
[X] streaming response
[ ] Chatbot with memory
[X] FastAPI integration
[X] Streaming response
[ ] A front-end for chat
[ ] Tool use, calculator tool to execute R command
[ ] MCP call
[ ] RAG (maybe adaptive RAG)
[ ] Bi-directional, websocket connection


### Things to consider
Pydantic AI
- Managing message history, use `history_processors`, functions: send 5 most recent messages, ignoring model response, etc.


FastAPI
- Lifecycle management
    - Handling what happens when the app start up and shut down