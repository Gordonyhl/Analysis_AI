import asyncio

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.settings import ModelSettings
from pydantic_core import to_jsonable_python
import json

load_dotenv()

gpt5 = "gpt-5"

gemini_model = GeminiModel('gemini-2.0-flash', provider = 'google-gla')
openai_model = OpenAIModel(gpt5, provider = 'openai')

agent = Agent(
    model = gemini_model,
    system_prompt = "you're a helpful assistant, answer concisely and to the point",
    model_settings=ModelSettings(temperature=1, max_tokens=500)
)

# async function to stream the response
async def main():
    # empty string for storing memory
    msg_history = []

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "q"]:
            break

        async with agent.run_stream(user_input, message_history=msg_history) as result:
            async for message in result.stream_text():
                print(message)

        messages = result.all_messages()
        msg_history = messages
        # Convert the history into a JSON-serializable Python object
        py_obj = to_jsonable_python(msg_history)
        json_str = json.dumps(py_obj, ensure_ascii=False, indent=2)
        print(json_str) # print log

if __name__ == "__main__":
    asyncio.run(main())
    
"""
# code to be used later for chatbot with memory
message_history: List[ModelMessage] = []

while True:
    user_input = input("> ")
    if user_input.lower() in ["quit", "exit", "q"]:
        break

    result = agent.run_sync(user_input, message_history=message_history) # run the agent
    print(result.output) # print the result
    message_history = result.all_messages() """

