from langchain_core.messages import SystemMessage, HumanMessage
from uuid import uuid4
from shelp.prompt import SYS_PROMPT


def generate_id() -> str:
    """Generates UUID v4 and returns it as a string"""
    return str(uuid4())

def get_state_dict(user_input: str, with_prompt: bool = True):
    """generates a dict for the state of the graph, with or without the system prompt"""
    messages = [SystemMessage(SYS_PROMPT)] if with_prompt else []
    return {
        "messages": messages + [HumanMessage(user_input)],
        "final_response": None
    }


def is_tool_call(message):
    """Returns a boolean for whether the given message was a tool call"""
    return message.type == "tool"

def display_stream(stream):
    """
    Displays all messages in a stream of events, as they arrive, formatted in Markdown.
    Returns the last event to have access to the full list of messages even after the stream
    has been consumed
    """
    last = None
    for event in stream:
        messages = event["messages"]
        
        # Start from the end, collect messages until we hit a tool call
        to_display = [messages[-1]]

        for message in messages[-1::-1]:
            if not is_tool_call(message):
                break
            to_display.append(message)
    
        for message in reversed(to_display):
            print(message.pretty_print())

        last = event

    return last

def show_response(result):
    """Shows the resulting final_response contained in the given result of a graph invocation"""
    response = result["final_response"]
    print(f"COMMAND: {response.command}\nCONFIDENCE: {response.confidence}\nEXPLANATION: {response.explanation}")
