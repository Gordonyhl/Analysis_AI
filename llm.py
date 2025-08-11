import asyncio
import json
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
    prepare_default_thread_history,
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


async def main() -> None:
    """Interactive CLI chat that persists history in Postgres.

    Flow per turn:
    - Load recent history for the default thread from Postgres
    - Stream the assistant reply while buffering the text
    - Append the user and assistant messages back to Postgres so conversation persists
    """
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "q"]:
            break

        thread_id, msg_history = await prepare_default_thread_history(
            limit=settings.ai_history_limit
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

