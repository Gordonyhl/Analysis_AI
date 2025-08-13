import asyncio
import json
import uuid
from typing import List

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.settings import ModelSettings
from pydantic_core import to_jsonable_python

from settings import settings
from storage import (
    append_messages,
    get_or_create_thread_by_title,
    load_recent_messages_for_thread,
)


load_dotenv()

gpt5 = "gpt-5"

gemini_model = GeminiModel("gemini-2.0-flash", provider="google-gla")
openai_model = OpenAIModel(gpt5, provider="openai")

agent = Agent(
    model=gemini_model,
    system_prompt="you're a helpful assistant, answer concisely and to the point",
    model_settings=ModelSettings(temperature=1, max_tokens=500),
)


async def select_thread() -> uuid.UUID:
    """Allow user to select or create a new conversation thread."""
    print("Select a conversation thread:")
    print("1. Use default thread")
    print("2. Enter a thread title to create/use")
    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "2":
        title = input("Enter thread title: ").strip()
        if title:
            return await get_or_create_thread_by_title(title)
    
    # Default thread
    return await get_or_create_thread_by_title(settings.thread_title)


async def main() -> None:
    """Interactive CLI chat that persists history in Postgres.

    Flow per turn:
    - Select or create a conversation thread
    - Load recent history for the selected thread from Postgres
    - Stream the assistant reply while buffering the text
    - Append the user and assistant messages back to Postgres so conversation persists
    """
    thread_id = await select_thread()
    print(f"Using thread ID: {thread_id}")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "q"]:
            break

        # Load recent history for the selected thread
        msg_history = await load_recent_messages_for_thread(
            thread_id, limit=settings.ai_history_limit
        )

        assistant_chunks: List[str] = []
        async with agent.run_stream(user_input, message_history=msg_history) as result:
            async for message in result.stream_text():
                print(message, end="")
                assistant_chunks.append(message)
            print()  # newline after stream

        assistant_text = "".join(assistant_chunks)

        # Persist both user and assistant messages in order
        await append_messages(
            thread_id,
            [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": assistant_text},
            ],
        )

        # Optional: print the fully structured message history returned by the model
        messages = result.all_messages()
        py_obj = to_jsonable_python(messages)
        json_str = json.dumps(py_obj, ensure_ascii=False, indent=2)
        print(json_str)


if __name__ == "__main__":
    asyncio.run(main())

