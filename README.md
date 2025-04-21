# Shelp

## What is it
Shelp is  a command line tool for unix platforms that lets users specify operations to perform using natural language.
In addition to shell commands, I thought that it would be useful to let it craft SQL queries. 
The tool is not able to execute arbitrary code, it can only suggest a command accompanied by an explanation. It's up to the user to inspect the proposed solution and decide whether to execute it.

## Why I thought of it
I work as a Software Developer and I spend a decent amount of time interacting with a shell. 
Sometimes I have a task to perform but I don't remember off the top of my head the correct combination of commands to complete it. 
I built this tool to reduce the friction of switching contexts when working in the shell. Instead of searching online for the correct command syntax, `shelp` lets me generate commands directly from natural language — saving time and keeping me in flow.

## Technologies used
- **Gemini Flash 2.0**: Core LLM for understanding and generating commands.
- **LangGraph**: Controls the agent's stateful flow and tool usage
- **SQLAlchemy**: Enables SQL schema introspection and dialect abstraction.