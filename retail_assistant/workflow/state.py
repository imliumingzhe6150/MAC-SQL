from typing import Any, Literal, TypedDict


class RAGState(TypedDict, total=False):
    # 用户输入与检索参数
    question: str
    candidate_k: int
    rerank_k: int
    top_k: int

    # 混合检索输出：尚未重排的候选
    index_version: str
    candidate_hits: list[dict[str, Any]]

    # 重排输出：最终送入回答的证据
    hits: list[dict[str, Any]]
    rerank_status: Literal["ok", "fallback", "empty"]
    rerank_error: str | None
    rerank_elapsed_ms: float

    # 回答节点输出
    answer: str
    citations: list[dict[str, Any]]