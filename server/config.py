from openai import OpenAI
import re
from pydantic_settings import BaseSettings, SettingsConfigDict
 
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Physics RAG"
    database_url: str

    vllm_base_url: str
    chat_model: str
    embedding_model: str
    embedding_base_url: str | None = None
    embedding_api_model: str | None = None
    rerank_base_url: str | None = None
    rerank_api_model: str | None = None

    num_sources: int = 5
    min_source_score: float = 0.0

    hybrid_search_enabled: bool = True
    query_rewrite_enabled: bool = True
    rerank_enabled: bool = True
    rerank_candidates: int = 15
    fetch_multiplier: int = 3

    llamaparse_api_key: str | None = None

    embedding_dim: int = 1024
    embedding_batch_size: int = 200

    chunk_min_size: int = 200
    chunk_max_size: int = 1500
    semantic_chunking_enabled: bool = False 

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440


settings = Settings() #pyright: ignore[reportCallIssue]

_client = OpenAI(
    base_url=settings.vllm_base_url,
    api_key="placeholder"
)

_embedding_client: OpenAI | None = None

def get_embedding_client() -> OpenAI | None:
    global _embedding_client
    if _embedding_client is None and settings.embedding_base_url:
        _embedding_client = OpenAI(
            base_url=settings.embedding_base_url,
            api_key="placeholder",
        )
    return _embedding_client

_rerank_client: OpenAI | None = None

def get_rerank_client() -> OpenAI | None:
    global _rerank_client
    if _rerank_client is None and settings.rerank_base_url:
        _rerank_client = OpenAI(
            base_url=settings.rerank_base_url,
            api_key="placeholder",
        )
    return _rerank_client

_THINK_RE = re.compile(r"<think>(.*?)</think>\s*", re.DOTALL)

def _split_think(raw: str) -> tuple[str, str | None]:
    m = _THINK_RE.match(raw)
    if m:
        think = m.group(1).strip()
        answer = raw[m.end():].strip()
        return answer, think
    return raw.strip(), None


_SAMPLING_PRESETS = {
    "rewrite":  {"temperature": 0.7, "top_p": 0.8, "top_k": 40, "min_p": 0.0, "presence_penalty": 1.5, "repetition_penalty": 1.0},
    "rerank":   {"temperature": 1.0, "top_p": 0.95, "top_k": 40, "min_p": 0.0, "presence_penalty": 1.5, "repetition_penalty": 1.0},
    "general":  {"temperature": 0.7, "top_p": 0.8, "top_k": 40, "min_p": 0.0, "presence_penalty": 1.5, "repetition_penalty": 1.0},
}
_THINKING_PARAMS = {"temperature": 1.0, "top_p": 0.95, "top_k": 40, "min_p": 0.0, "presence_penalty": 0.0, "repetition_penalty": 1.0}


def llm_call(
    system: str,
    user: str,
    max_tokens: int = 20480,
    json_schema: dict | None = None,
    json_schema_name: str = "response",
    *,
    task: str | None = None,
    stream: bool = False,
):
    """Call the LLM. Returns (answer, think) or a token generator if stream=True."""
    kwargs: dict = {}
    if json_schema is not None:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": json_schema_name, "schema": json_schema},
        }

    if task is not None:
        if task not in _SAMPLING_PRESETS:
            raise ValueError(f"Unknown task {task!r}. Choose from: {list(_SAMPLING_PRESETS)}")
        p = _SAMPLING_PRESETS[task]
        extra = {**p, "chat_template_kwargs": {"enable_thinking": False}}
    else:
        p = _THINKING_PARAMS
        extra = {**p, "chat_template_kwargs": {"enable_thinking": json_schema is None}}

    resp = _client.chat.completions.create(
        model=settings.chat_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=max_tokens,
        stream=True,
        extra_body=extra,
        **kwargs,
    )

    if stream:
        def _stream():
            for chunk in resp:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        return _stream()

    raw = ""
    for chunk in resp:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            raw += delta.content
    return _split_think(raw)
