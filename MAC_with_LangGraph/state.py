from typing import Any, Literal, TypedDict

class SQLState(TypedDict, total = False):
    question: str
    db_id: str

    schema_text: str
    foreign_keys: str

    sql: str
    execution: dict[str, Any]

    retry_count: int
    max_retries: int

    status: Literal["succeeded", "failed", "running"]
    answer: str