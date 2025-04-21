import os
import sys
from shelp import graph, utils


class App:
    def __init__(self):
        self.graph = graph.create()

    
    def start_conversation(self, user_input: str, stream: bool = False):
        """
        Starts a conversation with the model (optionally in stream mode) and 
        returns a tuple with the conversation id (str) and a stream if required, else the result
        """
        conversation_id = utils.generate_id()
        config = {"configurable": {"thread_id": conversation_id}}
        args = [utils.get_state_dict(user_input), config]

        if stream:
            result = self.graph.stream(*args, stream_mode="values")
        else:
            result = self.graph.invoke(*args)
            
        return conversation_id, result

    def resume_conversation(self, conversation_id: str, user_input: str, stream: bool = False):
        """
        Resumes a conversation with the given id and with new user input.
        If stream is true, returns a stream of messages, otherwise returns only
        the final result of the graph invocation.
        """
        config = {"configurable": {"thread_id": conversation_id}}
        args = [utils.get_state_dict(user_input, with_prompt=False), config]

        if stream:
            return self.graph.stream(*args, stream_mode="values")

        return self.graph.invoke(*args)

def main():
    args = sys.argv[1:]
    if len(args) == 0:
        raise ValueError("USAGE: shelp [query]")

    if os.environ.get("GOOGLE_API_KEY", None) is None:
        raise ValueError("please provide your google api key in GOOGLE_API_KEY")
    
    app = App()
    _conversation_id, result = app.start_conversation(" ".join(args))
    utils.show_response(result)

if __name__ == "__main__":
    main()
