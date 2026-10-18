import os
from functools import lru_cache

from langchain_deepseek import ChatDeepSeek


@lru_cache(maxsize=1)
def _get_model() -> ChatDeepSeek:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("请先设置 DEEPSEEK_API_KEY 环境变量。")

    return ChatDeepSeek(
        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"),
        api_key=api_key,
        base_url="https://api.deepseek.com",
        temperature=0,
        max_tokens=1024,
        timeout=60,
        max_retries=0,
        extra_body={"thinking": {"type": "disabled"}},
    )


def call_llm(prompt: str) -> str:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt 必须是非空字符串。")

    response = _get_model().invoke(prompt)

    if response.response_metadata.get("finish_reason") == "length":
        raise RuntimeError("模型输出达到长度上限，响应不完整。请检查提示词或调整 max_tokens。")

    content = response.content
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("模型未返回非空的文本回答。")

    return content.strip()


if __name__ == "__main__":
    from getpass import getpass

    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        os.environ["DEEPSEEK_API_KEY"] = getpass("请输入 DeepSeek API Key：").strip()

    print(call_llm("请只回答：连接成功"))
