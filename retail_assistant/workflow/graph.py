import argparse
import os
from getpass import getpass

from langgraph.graph import END, START, StateGraph

from retail_assistant.workflow.nodes import (
    generate_answer,
    rerank_knowledge,
    retrieve_knowledge,
)
from retail_assistant.workflow.state import RAGState


builder = StateGraph(RAGState)

builder.add_node("retrieve_knowledge", retrieve_knowledge)
builder.add_node("rerank_knowledge", rerank_knowledge)
builder.add_node("generate_answer", generate_answer)

builder.add_edge(START, "retrieve_knowledge")
builder.add_edge("retrieve_knowledge", "rerank_knowledge")
builder.add_edge("rerank_knowledge", "generate_answer")
builder.add_edge("generate_answer", END)

graph = builder.compile()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RetailOps 知识问答"
    )
    parser.add_argument("question")
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--rerank-k", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--show-hits", action="store_true")
    args = parser.parse_args()

    if not args.question.strip():
        parser.error("问题不能为空")

    if not 1 <= args.top_k <= args.rerank_k <= args.candidate_k:
        parser.error(
            "要求 candidate-k >= rerank-k >= top-k >= 1"
        )

    if args.rerank_k > 500:
        parser.error("rerank-k 不能超过 500")

    if not os.environ.get("RERANK_URL", "").strip():
        parser.error("请先设置 RERANK_URL")

    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        os.environ["DASHSCOPE_API_KEY"] = getpass(
            "请输入百炼 API Key："
        ).strip()

    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        os.environ["DEEPSEEK_API_KEY"] = getpass(
            "请输入 DeepSeek API Key："
        ).strip()

    initial_state: RAGState = {
        "question": args.question,
        "candidate_k": args.candidate_k,
        "rerank_k": args.rerank_k,
        "top_k": args.top_k,
    }

    result = graph.invoke(initial_state)

    print(
        f"\n重排状态：{result['rerank_status']}，"
        f"耗时：{result['rerank_elapsed_ms']:.0f} ms"
    )

    if result["rerank_error"]:
        print(f"降级原因：{result['rerank_error']}")

    if args.show_hits:
        print(
            f"\nRRF 候选数：{len(result['candidate_hits'])}，"
            f"最终证据数：{len(result['hits'])}"
        )

        for hit in result["hits"]:
            score = hit["rerank_score"]
            score_text = (
                "-" if score is None else f"{score:.4f}"
            )

            print(
                f"RRF #{hit['rrf_rank']} → 最终 #{hit['rank']} "
                f"| score={score_text} "
                f"| {hit['metadata']['title']} "
                f"| chunk_id={hit['chunk_id']}"
            )

    print("\n回答：")
    print(result["answer"])

    print("\n引用来源：")

    for citation in result["citations"]:
        sections = " / ".join(citation["sections"])

        print(
            f'[{citation["citation_id"]}] '
            f'{citation["title"]} '
            f'(v{citation["version"]})'
        )
        print(f'    文件：{citation["source_path"]}')
        print(f'    章节：{sections or "未标注章节"}')

    if not result["citations"]:
        print("本次回答没有文档引用。")