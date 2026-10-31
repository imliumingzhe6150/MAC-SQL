from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge" / "retail_ops"


@dataclass
class KnowledgeDocument:
    doc_id: str
    version: int
    title: str
    source_path: str
    content_hash: str
    metadata: dict[str, Any]
    body: str


def load_document(path: Path) -> KnowledgeDocument:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines(keepends=True)

    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: 缺少 YAML 元数据")

    closing_line = next(
        (
            i
            for i in range(1, len(lines))
            if lines[i].strip() == "---"
        ),
        None,
    )

    if closing_line is None:
        raise ValueError(f"{path}: YAML 元数据没有结束标记")

    metadata_text = "".join(lines[1:closing_line])
    metadata = yaml.safe_load(metadata_text)
    body = "".join(lines[closing_line + 1:])

    if not isinstance(metadata, dict):
        raise ValueError(f"{path}: 元数据必须是键值对象")

    for field in ("doc_id", "title", "doc_type", "status"):
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{path}: {field} 必须是非空字符串")

    version = metadata.get("version")
    if type(version) is not int or version < 1:
        raise ValueError(f"{path}: version 必须是正整数")

    if not body.strip():
        raise ValueError(f"{path}: 文档正文为空")

    return KnowledgeDocument(
        doc_id=metadata["doc_id"],
        version=version,
        title=metadata["title"],
        source_path=path.relative_to(PROJECT_ROOT).as_posix(),
        content_hash=sha256(raw).hexdigest(),
        metadata=metadata,
        body=body,
    )


def load_documents() -> list[KnowledgeDocument]:
    paths = sorted(KNOWLEDGE_ROOT.rglob("*.md"))

    if not paths:
        raise ValueError(f"没有找到知识文档：{KNOWLEDGE_ROOT}")

    documents = []
    seen = set()

    for path in paths:
        document = load_document(path)
        key = (document.doc_id, document.version)

        if key in seen:
            raise ValueError(f"文档 ID 与版本重复：{key}")

        seen.add(key)
        documents.append(document)

    return documents


if __name__ == "__main__":
    documents = load_documents()

    print(f"读取文档数：{len(documents)}")
    for document in documents:
        print(
            document.doc_id,
            document.version,
            len(document.body),
            document.source_path,
        )