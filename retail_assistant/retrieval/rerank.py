import json
import math
import os
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class RerankServiceError(RuntimeError):
    """重排服务暂时不可用，或返回了无效结果。"""


def rerank(
    question: str,
    hits: list[dict[str, Any]],
    top_k: int = 6,
) -> list[dict[str, Any]]:
    question = question.strip()

    if not question:
        raise ValueError("问题不能为空")

    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k 必须是正整数")

    if not hits:
        return []

    if len(hits) > 500:
        raise ValueError("首版重排候选数量不能超过 500")

    # 1. 读取独立的重排配置。
    api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    url = os.environ.get("RERANK_URL", "").strip()
    model = os.environ.get(
        "RERANK_MODEL", "qwen3-rerank"
    ).strip()

    if not api_key:
        raise ValueError("请先设置 DASHSCOPE_API_KEY")

    if not url or not model:
        raise ValueError(
            "请设置 RERANK_URL 和有效的 RERANK_MODEL"
        )

    if (
        urlsplit(url).scheme != "https"
        or not urlsplit(url).hostname
    ):
        raise ValueError(
            "RERANK_URL 必须是完整的 HTTPS 地址"
        )

    # 2. documents 与 hits 必须保持一一对应。
    documents = [
        (
            f"标题：{hit['metadata']['title']}\n"
            f"章节：{' / '.join(hit['metadata']['sections'])}\n"
            f"正文：{hit['text']}"
        )
        for hit in hits
    ]

    top_n = min(top_k, len(hits))

    payload = {
        "model": model,
        "input": {
            "query": question,
            "documents": documents,
        },
        "parameters": {
            "top_n": top_n,
            "return_documents": False,
        },
    }

    request = Request(
        url,
        data=json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    # 3. 调用服务。
    # 配置错误直接暴露；暂时性故障允许降级。
    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

    except HTTPError as exc:
        if exc.code in (408, 429) or 500 <= exc.code < 600:
            raise RerankServiceError(
                f"重排服务 HTTP {exc.code}"
            ) from exc

        raise ValueError(
            f"重排请求 HTTP {exc.code}，"
            "请检查地址、密钥、模型和输入限制"
        ) from exc

    except (URLError, TimeoutError, HTTPException) as exc:
        raise RerankServiceError(
            "重排服务连接失败或超时"
        ) from exc

    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RerankServiceError(
            "重排服务没有返回有效 JSON"
        ) from exc

    # 4. 检查服务响应，避免错误索引破坏引用。
    if not isinstance(data, dict):
        raise RerankServiceError("重排响应必须是对象")

    if data.get("code"):
        raise ValueError(
            f"重排接口报错：{data['code']}"
        )

    output = data.get("output")
    results = (
        output.get("results")
        if isinstance(output, dict)
        else None
    )

    if not isinstance(results, list) or len(results) != top_n:
        raise RerankServiceError(
            "重排结果数量或结构异常"
        )

    reranked_hits = []
    seen = set()

    for row in results:
        if not isinstance(row, dict):
            raise RerankServiceError(
                "重排结果条目必须是对象"
            )

        index = row.get("index")
        score = row.get("relevance_score")

        if (
            type(index) is not int
            or not 0 <= index < len(hits)
        ):
            raise RerankServiceError(
                "重排返回了越界或无效的索引"
            )

        if index in seen:
            raise RerankServiceError(
                "重排返回了重复索引"
            )

        if (
            type(score) not in (int, float)
            or not math.isfinite(score)
            or not 0 <= score <= 1
        ):
            raise RerankServiceError(
                "重排返回了无效分数"
            )

        seen.add(index)
        original = hits[index]

        reranked_hits.append({
            **original,
            "rrf_rank": original["rank"],
            "rerank_score": float(score),
        })

    # 5. 更新最终排名；保留原片段、来源和 RRF 信息。
    reranked_hits.sort(
        key=lambda hit: (
            -hit["rerank_score"],
            hit["rrf_rank"],
        )
    )

    for rank, hit in enumerate(reranked_hits, start=1):
        hit["rank"] = rank

    return reranked_hits