import argparse
import json
import os
from getpass import getpass
from typing import Any

from retail_assistant.retrieval.bm25 import retrieve as bm25_retrieve
from retail_assistant.retrieval.dense import retrieve as dense_retrieve


def rrf_fuse(
    ranked_lists: dict[str, list[dict[str, Any]]],
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    if type(rrf_k) is not int or rrf_k < 1:
        raise ValueError("rrf_k 必须是正整数")

    merged = {}

    for retriever_name, hits in ranked_lists.items():
        seen = set()

        for rank, hit in enumerate(hits, start=1):
            chunk_id = hit["chunk_id"]

            # 同一路检索中的同一片段只计一次。
            if chunk_id in seen:
                continue
            seen.add(chunk_id)

            if chunk_id not in merged:
                merged[chunk_id] = {
                    "chunk_id": chunk_id,
                    "text": hit["text"],
                    "metadata": hit["metadata"],
                    "rrf_score": 0.0,
                    "retrieval_ranks": {},
                }

            item = merged[chunk_id]
            item["rrf_score"] += 1.0 / (rrf_k + rank)
            item["retrieval_ranks"][retriever_name] = rank

    ranked_hits = sorted(
        merged.values(),
        key=lambda item: (
            -item["rrf_score"],
            item["chunk_id"],
        ),
    )

    for rank, hit in enumerate(ranked_hits, start=1):
        hit["rank"] = rank

    return ranked_hits

def retrieve(
    question: str,
    top_k: int = 3,
    candidate_k: int = 10,
    rrf_k: int = 60,
) -> dict[str, Any]:
    question = question.strip()

    if not question:
        raise ValueError("问题不能为空")

    for name, value in (
        ("top_k", top_k),
        ("candidate_k", candidate_k),
        ("rrf_k", rrf_k),
    ):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} 必须是正整数")

    if candidate_k < top_k:
        raise ValueError("candidate_k 不能小于 top_k")

    # 1. 两路分别召回候选片段。
    dense_result = dense_retrieve(
        question=question,
        top_k=candidate_k,
    )
    bm25_result = bm25_retrieve(
        question=question,
        top_k=candidate_k,
    )

    # 2. 防止索引更新期间混用不同版本的结果。
    if dense_result["index_version"] != bm25_result["index_version"]:
        raise RuntimeError("Dense 与 BM25 索引版本不一致，请重试")

    # 3. 融合排名，然后截取最终结果。
    fused_hits = rrf_fuse(
        {
            "dense": dense_result["hits"],
            "bm25": bm25_result["hits"],
        },
        rrf_k=rrf_k,
    )

    return {
        "question": question,
        "index_version": dense_result["index_version"],
        "hits": fused_hits[:top_k],
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Dense + BM25 混合检索"
    )
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--candidate-k", type=int, default=10)
    parser.add_argument("--rrf-k", type=int, default=60)
    args = parser.parse_args()

    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        os.environ["DASHSCOPE_API_KEY"] = getpass(
            "请输入百炼 API Key："
        ).strip()

    result = retrieve(
        question=args.question,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
        rrf_k=args.rrf_k,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )