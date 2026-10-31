import argparse
import json
import os
from getpass import getpass
from typing import Any

import chromadb

from retail_assistant.embeddings import get_embeddings
from retail_assistant.ingestion.build_index import MANIFEST_PATH
from retail_assistant.ingestion.load_documents import PROJECT_ROOT

def retrieve(question: str, top_k: int = 3) -> dict[str, Any]:
    question = question.strip()

    if not question:
        raise ValueError("问题不能为空")

    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k 必须是正整数")

    # 1. 读取当前已发布的索引清单。
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError("没有索引清单，请先运行 build_index")

    manifest = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )
    spec = manifest["spec"]
    chroma_path = PROJECT_ROOT / manifest["chroma_path"]

    if not (chroma_path / "chroma.sqlite3").is_file():
        raise FileNotFoundError("没有找到 Chroma 数据库")

    # 2. 确保问题与文档使用相同的向量配置。
    embeddings = get_embeddings()

    current_config = {
        "embedding_model": embeddings.model,
        "embedding_dimensions": embeddings.dimensions,
        "embedding_base_url": embeddings.openai_api_base,
    }

    for key, value in current_config.items():
        if spec[key] != value:
            raise RuntimeError(
                f"{key} 与索引配置不一致，请确认配置并重建索引"
            )

    # 3. 查询 Chroma 数据库。
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_collection(
        name = manifest["collection_name"],
        embedding_function = None,
    )

    collection_version = (collection.metadata or {}).get(
        "index_version"
    )
    if collection_version != manifest["index_version"]:
        raise RuntimeError("集合版本与索引清单不一致")

    count = collection.count()
    if count == 0 or count != manifest["chunk_count"]:
        raise RuntimeError("索引记录数异常，请重新运行 build_index")

    # 4. 将问题转成向量并执行检索。
    query_vector = embeddings.embed_query(question)

    if len(query_vector) != spec["embedding_dimensions"]:
        raise RuntimeError("问题向量维度与索引不一致")

    result = collection.query(
        query_embeddings = [query_vector],
        n_results=min(top_k, count),
        where={"status": "published"},
        include=["documents", "metadatas", "distances"],
    )

    # 5. 将 Chroma 的返回值整理为统一结果。
    hits = []

    rows = zip(
        result["ids"][0],
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
        strict=True,
    )

    for rank, (chunk_id, text, metadata, distance) in enumerate(
        rows,
        start=1,
    ):
        metadata = dict(metadata)
        metadata["sections"] = json.loads(
            metadata.pop("sections_json")
        )

        hits.append({
            "rank": rank,
            "chunk_id": chunk_id,
            "distance": float(distance),
            "text": text,
            "metadata": metadata,
        })

    return {
        "question": question,
        "index_version": manifest["index_version"],
        "hits": hits,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="检索业务知识")
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        os.environ["DASHSCOPE_API_KEY"] = getpass(
            "请输入百炼 API Key："
        ).strip()

    result = retrieve(args.question, top_k=args.top_k)
    print(json.dumps(result, ensure_ascii=False, indent=2))