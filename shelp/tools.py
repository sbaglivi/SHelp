import shutil
import subprocess
import os
from sqlalchemy import create_engine, inspect
from langchain_core.tools import tool

@tool
def is_installed(executable: str) -> bool:
    """Checks if an executable with the given name is installed

    Args:
        executable: The name of the executable, e.g. curl

    Returns:
        A boolean value: whether an executable with the given name is installed.
    """
    return shutil.which(executable) is not None

@tool
def get_command_info(command: str) -> str:
    """Retrieves information about a given command with man if available, otherwise with --help. If both attempts fail, it returns a failure message.

    Args:
        command: The name of the executable, e.g. curl

    Returns:
        A string containing documentation for the command if available, otherwise a failure message.
    """
    if is_installed("man"):
        try:
            return subprocess.check_output(["man", command], stderr=subprocess.DEVNULL, text=True, timeout=3)
        except subprocess.CalledProcessError:
            pass  # man page not found
        except subprocess.TimeoutExpired:
            return "man page timed out"

    # Fallback to --help
    for help_flag in ["--help", "-h"]:
        try:
            return subprocess.check_output([command, help_flag], stderr=subprocess.STDOUT, text=True, timeout=3)
        except Exception:
            continue

    return f"No documentation found for {command}."

@tool
def sql_commands_available() -> bool:
    """Checks if sql commands are available.
    
    Returns:
        A boolean value: whether sql commands can be executed.
    """
    return os.environ.get("CONNECTION_STRING", None) is not None

@tool
def list_tables() -> list[str]:
    """
    List all user-defined tables in the database.

    Supports both SQLite and PostgreSQL (or any SQLAlchemy-compatible database).
        
    Returns:
        List[str]: A list of table names present in the database.
    """
    engine = create_engine(os.environ.get("CONNECTION_STRING"))
    with engine.connect() as conn:
        inspector = inspect(conn)
        return inspector.get_table_names()


@tool
def get_table_schema(table_name: str) -> dict:
    """
    Retrieve detailed schema information for a specific table, including column types,
    nullability, defaults, primary keys, foreign keys, and indexes.

    Works with both SQLite and PostgreSQL databases.

    Args:
        table_name (str): The name of the table whose schema should be retrieved.

    Returns:
        Dict: A dictionary containing:
            - "columns": List of dictionaries with column metadata:
                - name (str)
                - type (str)
                - nullable (bool)
                - default (Any)
                - primary_key (bool)
                - foreign_key (str or None)
            - "indexes": List of dictionaries with index metadata:
                - name (str)
                - column_names (List[str])
                - unique (bool)
    """
    engine = create_engine(os.environ.get("CONNECTION_STRING"))
    with engine.connect() as conn:
        inspector = inspect(conn)

        # Get columns
        columns = inspector.get_columns(table_name)
        # Get primary keys
        pk_columns = set(inspector.get_pk_constraint(table_name).get("constrained_columns", []))
        # Get foreign keys
        fk_constraints = inspector.get_foreign_keys(table_name)
        fk_map = {col: f"{fk['referred_table']}.{fk['referred_columns'][0]}" 
                  for fk in fk_constraints for col in fk['constrained_columns']}
        # Get indexes
        indexes = inspector.get_indexes(table_name)

        schema = {
            "columns": [],
            "indexes": indexes,
        }

        for col in columns:
            schema["columns"].append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "default": col.get("default"),
                "primary_key": col["name"] in pk_columns,
                "foreign_key": fk_map.get(col["name"]),
            })

        return schema
