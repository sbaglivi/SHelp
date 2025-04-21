from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from shelp.tools import is_installed, get_command_info, list_tables, get_table_schema


class FinalResponse(BaseModel):
    command: str | None
    explanation: str
    confidence: float

def create():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
    )

    tools = [is_installed, get_command_info, list_tables, get_table_schema]
    llm_with_tools = llm.bind_tools(tools)


    structured_llm = llm.with_structured_output(FinalResponse)


    class State(TypedDict):
        messages: Annotated[list, add_messages]
        final_response: FinalResponse | None

    def chatbot(state: State):
        return {"messages": [llm_with_tools.invoke(state["messages"])], "final_response": None}

    def answer(state: State):
        response = structured_llm.invoke(state["messages"])
        return {
            "messages": [AIMessage(content=str(response))], # this is added instead of set to respones because of add messages in state def?
            "final_response": response
        }

    def route_from_chat(state: State) -> str:
        last_msg = state["messages"][-1]
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            return "tools"
        else:
            return "answer"

    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)
    tool_node = ToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_node("answer", answer)
    graph_builder.add_conditional_edges(
        "chatbot",
        route_from_chat
    )
    # Any time a tool is called, we return to the chatbot to decide the next step
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.set_entry_point("chatbot")


    conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
    memory = SqliteSaver(conn)
    return graph_builder.compile(checkpointer=memory)