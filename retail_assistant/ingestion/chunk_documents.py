import json
import re
from hashlib import sha256
from typing import Any

from retail_assistant.ingestion.load_documents import (
    KnowledgeDocument,
    load_documents,
)


def split_document(
    document: KnowledgeDocument,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[dict[str, Any]]:
    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError("要求 chunk_size > 0，且 0 <= overlap < chunk_size")

    body = document.body
    strategy = f"fixed_chars_v1:size={chunk_size}:overlap={overlap}"

    # 记录标题位置，用于把分块对应到原文章节。
    headings = [
        (match.start(), match.group(1).strip())
        for match in re.finditer(
            r"^#{1,6}[ \t]+(.+)$",
            body,
            re.MULTILINE,
        )
    ]

    section_ranges = []
    for i, (start, title) in enumerate(headings):
        end = headings[i + 1][0] if i + 1 < len(headings) else len(body)
        section_ranges.append((start, end, title))

    chunks = []
    step = chunk_size - overlap

    for start in range(0, len(body), step):
        end = min(start + chunk_size, len(body))
        text = body[start:end]

        if text.strip():
            sections = [
                title
                for section_start, section_end, title in section_ranges
                if section_start < end and section_end > start
            ]

            identity = (
                f"{document.doc_id}|{document.version}|"
                f"{document.content_hash}|{strategy}|{start}|{end}"
            )
            chunk_id = sha256(identity.encode("utf-8")).hexdigest()

            chunks.append({
                "chunk_id": chunk_id,
                "doc_id": document.doc_id,
                "version": document.version,
                "title": document.title,
                "source_path": document.source_path,
                "content_hash": document.content_hash,
                "doc_type": document.metadata["doc_type"],
                "status": document.metadata["status"],
                "sections": sections,
                "start_char": start,
                "end_char": end,
                "chunking_strategy": strategy,
                "text": text,
            })

        if end == len(body):
            break

    return chunks


if __name__ == "__main__":
    documents = load_documents()
    published = [
        document
        for document in documents
        if document.metadata["status"] == "published"
    ]

    chunks = [
        chunk
        for document in published
        for chunk in split_document(document)
    ]

    print(f"已发布文档数：{len(published)}")
    print(f"分块数：{len(chunks)}")

    if chunks:
        print(json.dumps(chunks[0], ensure_ascii=False, indent=2))