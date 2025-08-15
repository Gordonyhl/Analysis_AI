### Badass checklist, each item build on top of each other
[X] streaming response \
[X] Chatbot with memory \
[X] FastAPI integration \
[X] Streaming response \
[X] HTTP post request for chatbot with memory (In Progress via API) \
[X] A front-end for chat (In Progress) \

[ ] Tool use, calculator tool to execute R command \
[ ] MCP call \
[ ] RAG (maybe adaptive RAG) \


### Things to consider
Pydantic AI
- Managing message history, use `history_processors`, functions: send 5 most recent messages, ignoring model response, etc.


FastAPI
- Lifecycle management
    - Handling what happens when the app start up and shut down