from langgraph.graph import START, END, StateGraph
import os
from getpass import getpass
from .state import SQLState
from .nodes import select_schema, generate_sql, execute_sql, route_after_execution, refine_sql, finish

builder = StateGraph(SQLState)

builder.add_node("select_schema", select_schema)
builder.add_node("generate_sql", generate_sql)
builder.add_node("execute_sql", execute_sql)
builder.add_node("refine_sql", refine_sql)
builder.add_node("finish", finish)

builder.add_edge(START, "select_schema")
builder.add_edge("select_schema", "generate_sql")
builder.add_edge("generate_sql", "execute_sql")

builder.add_conditional_edges("execute_sql", route_after_execution)

builder.add_edge("refine_sql", "execute_sql")
builder.add_edge("finish", END)

graph = builder.compile()

if __name__ == "__main__":
    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        os.environ["DEEPSEEK_API_KEY"] = getpass(
            "请输入 DeepSeek API Key："
        ).strip()
    initial_state: SQLState = {
       "question": (
        "Show the name and theme for all concerts "
        "and the number of singers in each concert."
        ),
        "db_id": "concert_singer",
         "retry_count": 0,
        "max_retries": 3,
    }

    result = graph.invoke(initial_state)

    print("生成的 SQL：", result["sql"])
    print("执行结果：", result["execution"])
    print("最终状态：", result["status"])
    print("最终回答：", result["answer"])