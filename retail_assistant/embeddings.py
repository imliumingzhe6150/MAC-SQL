import os
from functools import lru_cache
from getpass import getpass

from langchain_openai import OpenAIEmbeddings


EMBEDDING_MODEL = "text-embedding-v4"
EMBEDDING_DIMENSIONS = 1024


@lru_cache(maxsize=1)
def get_embeddings() -> OpenAIEmbeddings:
    api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()

    if not api_key:
        raise ValueError("请先设置 DASHSCOPE_API_KEY")

    base_url = os.environ.get(
        "DASHSCOPE_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ).strip()

    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        dimensions=EMBEDDING_DIMENSIONS,
        api_key=api_key,
        base_url=base_url,
        chunk_size=10,
        check_embedding_ctx_length=False,
        request_timeout=30,
        max_retries=0,
    )


if __name__ == "__main__":
    if not os.environ.get("DASHSCOPE_API_KEY", "").strip():
        os.environ["DASHSCOPE_API_KEY"] = getpass(
            "请输入百炼 API Key："
        ).strip()

    embeddings = get_embeddings()

    texts = [
        "延迟率按实际交付和预计交付的日历日期比较。",
        "支付记录金额不再乘以分期期数。",
    ]

    document_vectors = embeddings.embed_documents(texts)
    query_vector = embeddings.embed_query(
        "预计今天送到，晚上八点收到算延迟吗？"
    )

    if len(document_vectors) != len(texts):
        raise RuntimeError("返回的文档向量数量不正确")

    all_vectors = document_vectors + [query_vector]
    if any(
        len(vector) != EMBEDDING_DIMENSIONS
        for vector in all_vectors
    ):
        raise RuntimeError("返回的向量维度不正确")

    print(f"模型：{EMBEDDING_MODEL}")
    print(f"文档向量数量：{len(document_vectors)}")
    print(f"文档向量维度：{len(document_vectors[0])}")
    print(f"问题向量维度：{len(query_vector)}")