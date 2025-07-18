"""Simple chat app example build with FastAPI.

Run with:

    uv run -m pydantic_ai_examples.chat_app
"""

from __future__ import annotations as _annotations

# ============================================================================
# IMPORTS AND DEPENDENCIES
# ============================================================================
# All necessary imports for the chat application including:
# - Standard library modules for async operations, JSON handling, SQLite, etc.
# - FastAPI for web framework
# - Pydantic AI for AI agent functionality
# - Logfire for observability and monitoring

import asyncio
import json
import sqlite3
from collections.abc import AsyncIterator
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Annotated, Any, Callable, Literal, TypeVar

import fastapi
import logfire
from fastapi import Depends, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from typing_extensions import LiteralString, ParamSpec, TypedDict

from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

# ============================================================================
# CONFIGURATION AND INITIALIZATION
# ============================================================================
# Setup observability with Logfire and initialize the AI agent

# Configure Logfire for monitoring - only sends data if token is present
# 'if-token-present' means nothing will be sent if you don't have logfire configured
logfire.configure(send_to_logfire='if-token-present')
logfire.instrument_pydantic_ai()

# Initialize the AI agent with OpenAI's GPT-4o model
agent = Agent('openai:gpt-4o')
THIS_DIR = Path(__file__).parent

# ============================================================================
# FASTAPI APPLICATION SETUP
# ============================================================================
# Configure the FastAPI application with database lifecycle management

@asynccontextmanager
async def lifespan(_app: fastapi.FastAPI):
    """Application lifespan manager that handles database connection lifecycle.
    
    This ensures the database connection is established when the app starts
    and properly closed when the app shuts down.
    """
    async with Database.connect() as db:
        yield {'db': db}


# Create FastAPI application with the lifespan context manager
app = fastapi.FastAPI(lifespan=lifespan)
# Enable FastAPI monitoring with Logfire
logfire.instrument_fastapi(app)

# ============================================================================
# STATIC FILE SERVING ENDPOINTS
# ============================================================================
# Routes that serve the HTML and TypeScript files for the frontend

@app.get('/')
async def index() -> FileResponse:
    """Serve the main HTML file for the chat application frontend."""
    return FileResponse((THIS_DIR / 'chat_app.html'), media_type='text/html')


@app.get('/chat_app.ts')
async def main_ts() -> FileResponse:
    """Get the raw typescript code, it's compiled in the browser, forgive me."""
    return FileResponse((THIS_DIR / 'chat_app.ts'), media_type='text/plain')

# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================
# FastAPI dependency to provide database access to endpoints

async def get_db(request: Request) -> Database:
    """FastAPI dependency that extracts the database instance from request state.
    
    This allows endpoints to access the database connection that was established
    during application startup.
    """
    return request.state.db

# ============================================================================
# DATA MODELS AND TYPE DEFINITIONS
# ============================================================================
# TypedDict for structuring chat messages sent to the browser

class ChatMessage(TypedDict):
    """Format of messages sent to the browser.
    
    Defines the structure of chat messages that the frontend expects,
    including role (user/model), timestamp, and content.
    """

    role: Literal['user', 'model']
    timestamp: str
    content: str

# ============================================================================
# MESSAGE CONVERSION UTILITIES
# ============================================================================
# Functions to convert between internal message formats and frontend format

def to_chat_message(m: ModelMessage) -> ChatMessage:
    """Convert internal ModelMessage to frontend ChatMessage format.
    
    Takes Pydantic AI's internal message format and converts it to the
    simplified format expected by the frontend. Handles both user requests
    and model responses.
    """
    first_part = m.parts[0]
    if isinstance(m, ModelRequest):
        if isinstance(first_part, UserPromptPart):
            assert isinstance(first_part.content, str)
            return {
                'role': 'user',
                'timestamp': first_part.timestamp.isoformat(),
                'content': first_part.content,
            }
    elif isinstance(m, ModelResponse):
        if isinstance(first_part, TextPart):
            return {
                'role': 'model',
                'timestamp': m.timestamp.isoformat(),
                'content': first_part.content,
            }
    raise UnexpectedModelBehavior(f'Unexpected message type for chat app: {m}')

# ============================================================================
# CHAT API ENDPOINTS
# ============================================================================
# HTTP endpoints that handle chat functionality

@app.get('/chat/')
async def get_chat(database: Database = Depends(get_db)) -> Response:
    """Retrieve all existing chat messages from the database.
    
    Returns the chat history as newline-delimited JSON messages.
    Used by the frontend to load previous conversation history.
    """
    msgs = await database.get_messages()
    return Response(
        b'\n'.join(json.dumps(to_chat_message(m)).encode('utf-8') for m in msgs),
        media_type='text/plain',
    )


@app.post('/chat/')
async def post_chat(
    prompt: Annotated[str, fastapi.Form()], database: Database = Depends(get_db)
) -> StreamingResponse:
    """Handle new chat messages and stream AI responses.
    
    This endpoint:
    1. Receives a user prompt via form data
    2. Immediately streams the user message to the frontend
    3. Retrieves chat history for context
    4. Runs the AI agent with streaming response
    5. Streams AI response chunks to the frontend in real-time
    6. Saves the conversation to the database
    """
    async def stream_messages():
        """Streams new line delimited JSON `Message`s to the client."""
        # stream the user prompt so that can be displayed straight away
        yield (
            json.dumps(
                {
                    'role': 'user',
                    'timestamp': datetime.now(tz=timezone.utc).isoformat(),
                    'content': prompt,
                }
            ).encode('utf-8')
            + b'\n'
        )
        # get the chat history so far to pass as context to the agent
        messages = await database.get_messages()
        # run the agent with the user prompt and the chat history
        async with agent.run_stream(prompt, message_history=messages) as result:
            async for text in result.stream(debounce_by=0.01):
                # text here is a `str` and the frontend wants
                # JSON encoded ModelResponse, so we create one
                m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp())
                yield json.dumps(to_chat_message(m)).encode('utf-8') + b'\n'

        # add new messages (e.g. the user prompt and the agent response in this case) to the database
        await database.add_messages(result.new_messages_json())

    return StreamingResponse(stream_messages(), media_type='text/plain')

# ============================================================================
# TYPE DEFINITIONS FOR DATABASE CLASS
# ============================================================================
# Generic type variables used in the Database class for type safety

P = ParamSpec('P')
R = TypeVar('R')

# ============================================================================
# DATABASE MANAGEMENT CLASS
# ============================================================================
# Handles SQLite database operations with async support

@dataclass
class Database:
    """Rudimentary database to store chat messages in SQLite.

    The SQLite standard library package is synchronous, so we
    use a thread pool executor to run queries asynchronously.
    
    This class provides:
    - Async database connection management
    - Message storage and retrieval
    - Thread pool execution for sync SQLite operations
    """

    con: sqlite3.Connection
    _loop: asyncio.AbstractEventLoop
    _executor: ThreadPoolExecutor

    @classmethod
    @asynccontextmanager
    async def connect(
        cls, file: Path = THIS_DIR / '.chat_app_messages.sqlite'
    ) -> AsyncIterator[Database]:
        """Create and manage database connection lifecycle.
        
        This context manager:
        1. Sets up async event loop and thread pool
        2. Creates SQLite connection and initializes schema
        3. Instruments connection with Logfire for monitoring
        4. Ensures proper cleanup when done
        """
        with logfire.span('connect to DB'):
            loop = asyncio.get_event_loop()
            executor = ThreadPoolExecutor(max_workers=1)
            con = await loop.run_in_executor(executor, cls._connect, file)
            slf = cls(con, loop, executor)
        try:
            yield slf
        finally:
            await slf._asyncify(con.close)

    @staticmethod
    def _connect(file: Path) -> sqlite3.Connection:
        """Establish SQLite connection and create schema.
        
        Creates the messages table if it doesn't exist and sets up
        Logfire instrumentation for query monitoring.
        """
        con = sqlite3.connect(str(file))
        con = logfire.instrument_sqlite3(con)
        cur = con.cursor()
        cur.execute(
            'CREATE TABLE IF NOT EXISTS messages (id INT PRIMARY KEY, message_list TEXT);'
        )
        con.commit()
        return con

    async def add_messages(self, messages: bytes):
        """Store new messages in the database.
        
        Takes serialized message data and inserts it into the SQLite database.
        Uses thread pool to run the synchronous SQLite operations asynchronously.
        """
        await self._asyncify(
            self._execute,
            'INSERT INTO messages (message_list) VALUES (?);',
            messages,
            commit=True,
        )
        await self._asyncify(self.con.commit)

    async def get_messages(self) -> list[ModelMessage]:
        """Retrieve all messages from the database and deserialize them.
        
        Fetches all message records, deserializes the JSON data back into
        ModelMessage objects, and returns them in chronological order.
        """
        c = await self._asyncify(
            self._execute, 'SELECT message_list FROM messages order by id'
        )
        rows = await self._asyncify(c.fetchall)
        messages: list[ModelMessage] = []
        for row in rows:
            messages.extend(ModelMessagesTypeAdapter.validate_json(row[0]))
        return messages

    def _execute(
        self, sql: LiteralString, *args: Any, commit: bool = False
    ) -> sqlite3.Cursor:
        """Execute SQL queries synchronously.
        
        Helper method that runs SQL commands and optionally commits transactions.
        This is called from the thread pool to avoid blocking the async event loop.
        """
        cur = self.con.cursor()
        cur.execute(sql, args)
        if commit:
            self.con.commit()
        return cur

    async def _asyncify(
        self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> R:
        """Run synchronous functions asynchronously using thread pool.
        
        This utility method allows us to run SQLite's synchronous operations
        in a thread pool so they don't block the main async event loop.
        """
        return await self._loop.run_in_executor(  # type: ignore
            self._executor,
            partial(func, **kwargs),
            *args,  # type: ignore
        )

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================
# Development server configuration when running the script directly

if __name__ == '__main__':
    import uvicorn

    # Run the development server with auto-reload for development
    uvicorn.run(
        'pydantic_ai_examples.chat_app:app', reload=True, reload_dirs=[str(THIS_DIR)]
    )