import asyncio
import uuid
from typing import AsyncGenerator, List

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.settings import ModelSettings

from settings import settings
from storage import (
    append_messages,
    get_or_create_thread_by_title,
    load_recent_messages_for_thread,
)


load_dotenv()

gemini_model = GeminiModel("gemini-2.0-flash", provider="google-gla")

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


async def stream_chat_response(
    user_input: str,
    *,
    thread_title: str | None = None,
    thread_id: uuid.UUID | None = None,
) -> AsyncGenerator[str, None]:
    """Stream assistant response for a user message and persist the conversation.

    Args:
        user_input: The incoming user message.
        thread_title: Optional title for the thread; used if ``thread_id`` is not provided.
        thread_id: Existing thread identifier to use.

    Yields:
        Chunks of the assistant's response as they are produced.
    """

    if thread_id is None:
        thread_id = await get_or_create_thread_by_title(
            thread_title or settings.thread_title
        )

    msg_history = await load_recent_messages_for_thread(
        thread_id, limit=settings.ai_history_limit
    )

    last_yielded_text = ""
    final_assistant_text = ""
    async with agent.run_stream(user_input, message_history=msg_history) as result:
        # Manually calculate the delta to ensure correct streaming behavior
        async for cumulative_text in result.stream_text(delta=False):
            delta = cumulative_text[len(last_yielded_text):]
            if delta:
                yield delta
                last_yielded_text = cumulative_text
    
    final_assistant_text = last_yielded_text

    await append_messages(
        thread_id,
        [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": final_assistant_text},
        ],
    )


async def main() -> None:
    """Interactive CLI chat that persists history in Postgres."""
    thread_id = await select_thread()
    print(f"Using thread ID: {thread_id}")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "q"]:
            break

        async for chunk in stream_chat_response(user_input, thread_id=thread_id):
            print(chunk, end="")
        print()


if __name__ == "__main__":
    asyncio.run(main())

