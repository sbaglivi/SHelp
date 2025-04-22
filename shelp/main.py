import sys
import os
import requests
import json
import shutil
import subprocess
import sqlite3
from shelp.prompt import SYS_PROMPT

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# --- Tool implementations (minimal, no extra deps) ---
def is_installed(executable):
    return shutil.which(executable) is not None

def get_command_info(command):
    if is_installed("man"):
        try:
            return subprocess.check_output(["man", command], stderr=subprocess.DEVNULL, text=True, timeout=3)
        except Exception:
            pass
    for help_flag in ["--help", "-h"]:
        try:
            return subprocess.check_output([command, help_flag], stderr=subprocess.STDOUT, text=True, timeout=3)
        except Exception:
            continue
    return f"No documentation found for {command}."

def list_tables():
    conn_str = os.environ.get("CONNECTION_STRING")
    if not conn_str or not conn_str.startswith("sqlite"):
        return []
    path = conn_str.split("///")[-1]
    try:
        with sqlite3.connect(path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            return [row[0] for row in cur.fetchall()]
    except Exception:
        return []

def get_table_schema(table_name):
    conn_str = os.environ.get("CONNECTION_STRING")
    if not conn_str or not conn_str.startswith("sqlite"):
        return {}
    path = conn_str.split("///")[-1]
    try:
        with sqlite3.connect(path) as conn:
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table_name});")
            columns = cur.fetchall()
            return {"columns": [{
                "name": col[1],
                "type": col[2],
                "nullable": not col[3],
                "default": col[4],
                "primary_key": bool(col[5]),
            } for col in columns]}
    except Exception:
        return {}

# --- Main Gemini interaction loop ---
def call_gemini(messages, tools=None, api_key=None, system_instruction=None):
    url = f"{GEMINI_API_URL}?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": messages,
    }
    if system_instruction:
        payload["system_instruction"] = {"parts": [{"text": system_instruction}]}
    if tools:
        payload["tools"] = tools
    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
    response.raise_for_status()
    return response.json()

def main():
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        user_input = input("Enter your instruction: ")
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Please set GOOGLE_API_KEY in your environment.")
        sys.exit(1)
    messages = [{"role": "user", "parts": [{"text": user_input}]}]
    tools = [
        {"functionDeclarations": [
            {"name": "is_installed", "description": "Checks if a shell command is installed", "parameters": {"type": "object", "properties": {"executable": {"type": "string"}}, "required": ["executable"]}},
            {"name": "get_command_info", "description": "Gets documentation for a shell command", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
            {"name": "list_tables", "description": "Lists all tables in the sqlite database", "parameters": {"type": "object", "properties": {}}},
            {"name": "get_table_schema", "description": "Gets schema for a table in sqlite", "parameters": {"type": "object", "properties": {"table_name": {"type": "string"}}, "required": ["table_name"]}},
        ]}
    ]
    first_turn = True
    while True:
        if first_turn:
            result = call_gemini(messages, tools=tools, api_key=api_key, system_instruction=SYS_PROMPT)
            first_turn = False
        else:
            result = call_gemini(messages, tools=tools, api_key=api_key)
        parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        if not parts:
            print("No response from Gemini.")
            break
        # Handle multiple function calls in one turn
        function_calls = [p for p in parts if isinstance(p, dict) and p.get("functionCall")]
        if function_calls:
            for part in function_calls:
                fn = part["functionCall"]["name"]
                args = part["functionCall"].get("args", {})
                if fn == "is_installed":
                    res = is_installed(args.get("executable"))
                elif fn == "get_command_info":
                    res = get_command_info(args.get("command"))
                elif fn == "list_tables":
                    res = list_tables()
                elif fn == "get_table_schema":
                    res = get_table_schema(args.get("table_name"))
                else:
                    res = None
                messages.append({"role": "function", "parts": [{"functionResponse": {"name": fn, "response": res}}]})
            continue
        # No function calls: enforce structured output for final response
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "nullable": True},
                    "explanation": {"type": "string"},
                    "confidence": {"type": "number"}
                },
                "required": ["command", "explanation", "confidence"]
            }
        }
        payload = {
            "contents": messages,
            "generationConfig": generation_config
        }
        url = f"{GEMINI_API_URL}?key={api_key}"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        result = response.json()
        parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        try:
            data = json.loads(parts[0]["text"])
            print(f"COMMAND: {data.get('command')}\nCONFIDENCE: {data.get('confidence')}\nEXPLANATION: {data.get('explanation')}")
        except Exception:
            print(parts[0].get("text"))
        break

if __name__ == "__main__":
    main()
