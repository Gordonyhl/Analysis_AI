'''
testing, ignore this file for now 
'''


from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END, add_messages
from pydantic import BaseModel, Field
from langgraph.checkpoint.memory import InMemorySaver # short-term memory
from llm import agent

# state where the chatbot will have access to the messages
class State(TypedDict):
    messages: Annotated[list, add_messages] # add messages to the list

graph_builder = StateGraph(State)

def chat_agent(state: State):
    query = state["messages"][-1].content


graph_builder.add_node("chatbot", chat_agent) # define a node named "chatbot", that uses the chat_agent function

graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile()

user_input = input("Enter a message: ")

# invoke the graph with the user input, follow the format of the State class
state = graph.invoke({"messages": [{"role": "user", "content": user_input}]})

print(state["messages"][-1].content)