import json
import os
from getpass import getpass
from hashlib import sha256
from importlib.metadata import version as package_version
from typing import Any

import chromadb

from retail_assistant.embeddings import get_embeddings
from retail_assistant.ingestion.chunk_documents import split_document
from retail_assistant.ingestion.load_documents import (
    PROJECT_ROOT,
    load_documents,
)


INDEX_ROOT = PROJECT_ROOT / "outputs" / "retail_ops" / "index"
CHROMA_PATH = INDEX_ROOT / "chroma"
MANIFEST_PATH = INDEX_ROOT / "manifest.json"
BATCH_SIZE = 10


def to_metadata(chunk: dict[str, Any]) -> dict[str, Any]:
    metadata = {
        key: value
        for key, value in chunk.items()
        if key not in ("chunk_id", "text", "sections")
    }

    metadata["sections_json"] = json.dumps(
        chunk["sections"],
        ensure_ascii=False,
    )

    return metadata


def build_index() -> None:
    # 1. 加载已发布文档并分块。
    documents = [
        document
        for document in load_documents()
        if document.metadata["status"] == "published"
    ]

    chunks = [
        chunk
        for document in documents
        for chunk in split_document(document)
    ]

    if not chunks:
        raise ValueError("没有可建立索引的分块")

    chunk_ids = [chunk["chunk_id"] for chunk in chunks]

    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError("分块 ID 重复")

    embeddings = get_embeddings()

    # 2. 记录本次语料和模型配置，计算索引版本。
    spec = {
        "build_format": 1,
        "embedding_model": embeddings.model,
        "embedding_dimensions": embeddings.dimensions,
        "embedding_base_url": embeddings.openai_api_base,
        "embedding_input": "raw_chunk_text",
        "distance": "cosine",
        "sources": [
            {
                "doc_id": document.doc_id,
                "version": document.version,
                "source_path": document.source_path,
                "content_hash": document.content_hash,
            }
            for document in documents
        ],
        "chunk_ids": chunk_ids,
    }

    spec_text = json.dumps(
        spec,
        ensure_ascii=False,
        sort_keys=True,
    )
    index_version = sha256(spec_text.encode("utf-8")).hexdigest()
    collection_name = f"retail_ops_r0_{index_version[:20]}"

    # 3. 打开本地数据库，获取本版本对应的集合。
    INDEX_ROOT.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
        metadata={"index_version": index_version},
    )

    existing_ids = set(
        collection.get(include=["metadatas"])["ids"]
    )
    expected_ids = set(chunk_ids)

    if not existing_ids.issubset(expected_ids):
        raise RuntimeError("集合中存在不属于本次索引的分块")

    pending = [
        chunk
        for chunk in chunks
        if chunk["chunk_id"] not in existing_ids
    ]

    print(f"文档数：{len(documents)}")
    print(f"分块数：{len(chunks)}")
    print(f"已存在：{len(existing_ids)}")
    print(f"本次写入：{len(pending)}")

    # 4. 只对缺少的分块生成向量，分批写入。
    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start:start + BATCH_SIZE]
        texts = [chunk["text"] for chunk in batch]
        vectors = embeddings.embed_documents(texts)

        if len(vectors) != len(batch):
            raise RuntimeError("返回的向量数量不正确")

        if any(
            len(vector) != embeddings.dimensions
            for vector in vectors
        ):
            raise RuntimeError("返回的向量维度不正确")

        collection.upsert(
            ids=[chunk["chunk_id"] for chunk in batch],
            embeddings=vectors,
            documents=texts,
            metadatas=[to_metadata(chunk) for chunk in batch],
        )

        written = start + len(batch)
        print(f"已写入：{written}/{len(pending)}")

    # 5. 核对完整性，成功后发布当前索引清单。
    stored_ids = set(
        collection.get(include=["metadatas"])["ids"]
    )

    if stored_ids != expected_ids:
        raise RuntimeError("索引中的分块与预期不一致")

    manifest = {
        "index_version": index_version,
        "collection_name": collection_name,
        "chroma_path": CHROMA_PATH.relative_to(
            PROJECT_ROOT
        ).as_posix(),
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "chromadb_version": package_version("chromadb"),
        "spec": spec,
    }

    temporary_path = MANIFEST_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(MANIFEST_PATH)

    print(f"索引记录数：{collection.count()}")
    print(f"索引清单：{MANIFEST_PATH}")


if __name__ == "__main__":
    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        os.environ["DASHSCOPE_API_KEY"] = getpass(
            "请输入百炼 API Key："
        ).strip()

    build_index()