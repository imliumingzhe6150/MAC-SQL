import argparse
import json
import re
from typing import Any

import chromadb
import jieba
from rank_bm25 import BM25Okapi

from retail_assistant.ingestion.build_index import MANIFEST_PATH
from retail_assistant.ingestion.load_documents import PROJECT_ROOT


tokenizer = jieba.Tokenizer()

for word in ("延迟率", "支付记录", "分期期数", "订单项", "低评分率"):
    tokenizer.add_word(word)


def tokenize(text: str) -> list[str]:
    parts = re.findall(
        r"[a-z0-9_]+|[\u4e00-\u9fff]+",
        text.lower(),
    )

    tokens = []

    for part in parts:
        if re.fullmatch(r"[a-z0-9_]+", part):
            tokens.append(part)
        else:
            tokens.extend(
                word
                for word in tokenizer.lcut(part)
                if word.strip()
            )

    return tokens

def retrieve(
    question: str,
    top_k: int = 3,
) -> dict[str, Any]:
    question = question.strip()

    if not question:
        raise ValueError("问题不能为空")

    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k 必须是正整数")

    # 1. 读取当前索引清单。
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError("没有索引清单，请先运行 build_index")

    manifest = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )
    chroma_path = PROJECT_ROOT / manifest["chroma_path"]

    if not (chroma_path / "chroma.sqlite3").is_file():
        raise FileNotFoundError("没有找到 Chroma 数据库")

    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_collection(
        name=manifest["collection_name"],
        embedding_function=None,
    )

    collection_version = (collection.metadata or {}).get(
        "index_version"
    )
    if collection_version != manifest["index_version"]:
        raise RuntimeError("集合版本与索引清单不一致")

    count = collection.count()
    if count == 0 or count != manifest["chunk_count"]:
        raise RuntimeError("索引记录数异常，请重新运行 build_index")

    # 2. 读取允许检索的片段，在这个范围内建立 BM25。
    records = collection.get(
        where={"status": "published"},
        include=["documents", "metadatas"],
    )

    result = {
        "question": question,
        "index_version": manifest["index_version"],
        "hits": [],
    }

    query_tokens = tokenize(question)

    if not records["ids"] or not query_tokens:
        return result

    # 3. 文档与问题使用相同的分词规则。
    corpus_tokens = [
        tokenize(text)
        for text in records["documents"]
    ]

    if not any(corpus_tokens):
        return result

    bm25 = BM25Okapi(corpus_tokens)
    scores = bm25.get_scores(query_tokens)

    # 4. 只保留至少命中一个查询词的片段。
    query_terms = set(query_tokens)

    matched_indices = [
        index
        for index, tokens in enumerate(corpus_tokens)
        if query_terms.intersection(tokens)
    ]

    ranked_indices = sorted(
        matched_indices,
        key=lambda index: (
            -float(scores[index]),
            records["ids"][index],
        ),
    )[:top_k]

    # 5. 整理成与 Dense 接近的返回结构。
    hits = []

    for rank, index in enumerate(ranked_indices, start=1):
        metadata = dict(records["metadatas"][index])
        metadata["sections"] = json.loads(
            metadata.pop("sections_json")
        )

        hits.append({
            "rank": rank,
            "chunk_id": records["ids"][index],
            "score": float(scores[index]),
            "text": records["documents"][index],
            "metadata": metadata,
        })

    result["hits"] = hits

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BM25 业务知识检索"
    )
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    result = retrieve(
        question=args.question,
        top_k=args.top_k,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )