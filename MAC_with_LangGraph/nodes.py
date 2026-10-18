import sqlite3
import re
from .state import SQLState
from pathlib import Path
from typing import Literal
from .llm import call_llm

def select_schema(state: SQLState) -> dict[str, str]:
    project_root = Path(__file__).resolve().parents[1]
    db_id = state["db_id"]
    database_path = (
        project_root / "data" / "spider" / "database" / db_id / f"{db_id}.sqlite"
    )

    connection = sqlite3.connect(database_path.as_uri() + "?mode=ro", uri=True)

    try:
        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
                AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        schema_parts = []
        foreign_keys = []

        for (table_name,) in tables:
            columns = connection.execute(
                "SELECT name, type FROM pragma_table_info(?) ORDER BY cid",
                (table_name,),
            ).fetchall()

            column_text = ", ".join(f"{name} {col_type}" for name, col_type in columns)
            schema_parts.append(f"{table_name}({column_text})")

            keys = connection.execute(
                'SELECT "from", "table", "to" '
                'FROM pragma_foreign_key_list(?)',
                (table_name,),
            ).fetchall()

            for source_column, target_table, target_column in keys:
                foreign_keys.append(
                    f"{table_name}.{source_column}"
                    f" -> {target_table}.{target_column}"
                )
    
        return {
            "schema_text": "\n".join(schema_parts),
            "foreign_keys": "\n".join(foreign_keys),
        }
    finally:
        connection.close()



def generate_sql(state: SQLState) -> dict[str, str]:
    prompt = f"""
你负责将用户问题转换为 SQLite 查询。

要求：
1. 只使用提供的表和字段。
2. 生成一条只读查询，可以使用 SELECT 或 WITH。
3. 只返回 SQL，不要解释，不要使用 Markdown 代码块。

用户问题：
{state["question"]}

数据库表结构：
{state["schema_text"]}

外键关系：
{state["foreign_keys"]}
""".strip()

    reply = call_llm(prompt)

    match = re.fullmatch(
        r"```(?:sqlite|sql)?\s*(.*?)\s*```",
        reply,
        flags=re.IGNORECASE | re.DOTALL,
    )

    sql = match.group(1).strip() if match else reply.strip()
    return {"sql": sql}

def execute_sql(state: SQLState) -> dict:
    project_root = Path(__file__).resolve().parents[1]
    db_id = state["db_id"]
    database_path = (
        project_root / "data" / "spider" / "database" / db_id / f"{db_id}.sqlite"
    ) 

    connection = None

    try:
        connection = sqlite3.connect(
            database_path.as_uri() + "?mode=ro", uri=True
        )
        cursor = connection.execute(state["sql"])
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]

        return {
            "execution": {
                "success": True,
                "columns": columns,
                "rows": rows,
                "error": None,
            }
        }
    except sqlite3.Error as e:
        return {
            "execution": {
                "success": False,
                "columns": [],
                "rows": [],
                "error": str(e),
            }
        }
    finally:
        if connection:
            connection.close()

def route_after_execution(state: SQLState) -> Literal["finish", "refine_sql"]:
    if state["execution"]["success"]:
        return "finish"
    
    if state["retry_count"] >= state["max_retries"]:
        return "finish"

    return "refine_sql"

def finish(state: SQLState) -> dict[str, str]:
    if state["execution"]["success"]:
        return {
            "status": "succeeded",
            "answer": f"Query executed successfully. Result: {state['execution']['rows']}"
        }
    else:
        return {
            "status": "failed",
            "answer": f"Query execution failed. Error: {state['execution']['error']}"
        }

def refine_sql(state: SQLState) -> dict:
    prompt = f"""
你负责根据 SQLite 执行错误修正 SQL。

要求：
1. 保持用户原本的查询目标。
2. 只使用提供的表和字段。
3. 只返回一条修正后的只读 SQL，不要解释或 Markdown 代码块。

用户问题：
{state["question"]}

数据库表结构：
{state["schema_text"]}

外键关系：
{state["foreign_keys"]}

执行失败的 SQL：
{state["sql"]}

数据库错误：
{state["execution"]["error"]}
""".strip()

    reply = call_llm(prompt)

    match = re.fullmatch(
        r"```(?:sqlite|sql)?\s*(.*?)\s*```",
        reply,
        flags=re.IGNORECASE | re.DOTALL,
    )
    sql = match.group(1).strip() if match else reply.strip()

    return {
        "sql": sql,
        "retry_count": state["retry_count"] + 1,
        "execution": {},
    }