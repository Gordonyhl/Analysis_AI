import asyncio

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.settings import ModelSettings
from pydantic_core import to_jsonable_python
import json

load_dotenv()

gemini_model = GeminiModel('gemini-2.0-flash', provider = 'google-gla')
openai_model = OpenAIModel('gpt-4.1-mini', provider = 'openai')

agent = Agent(
    model = openai_model,
    system_prompt = "you're a helpful assistant, answer concisely and to the point",
    model_settings=ModelSettings(temperature=1, max_tokens=500) # for the sake of settings
)

# async function to stream the response
async def main():
    msg_history = []

    async with agent.run_stream('summarise software engineering in one sentence') as result:
        async for message in result.stream_text():  
            print(message)

    messages = result.all_messages()

    # Convert the history into a JSON-serializable Python object
    py_obj = to_jsonable_python(messages)
    json_str = json.dumps(py_obj, ensure_ascii=False, indent=2)
    print(json_str)

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