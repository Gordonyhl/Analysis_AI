from typing_extensions import TypedDict
from typing import Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph import add_messages
from pydantic_ai import Agent

from llm import agent
# 
class State(TypedDict):
    messages: Annotated[list, add_messages] # store the messages

graph_builder = StateGraph(State)

# You can now use the `model` object in your graph nodes.
def chatbot(state: State):
    # Convert the list of messages into a single string prompt
    prompt = "\n".join(
        f'{message["role"]}: {message["content"]}'
        for message in state["messages"]
    )
    response = agent.run_sync([prompt])
    # The agent returns a list of responses, we take the first one
    return {"messages": [("ai", response[0])]}


# define node, edges and compile graph
graph_builder.add_node("chatbot", chatbot)

graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile()

# to run the chatbot
user_input = input("User: ")
state = graph.invoke({"messages": [{"role": "user", "content": user_input}]})

print(state["messages"][-1].content)