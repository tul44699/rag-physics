import json
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from config import llm_call, get_rerank_client, settings
from embedding import embed_text


def _build_filters(
    textbook_ids: list[int] | None,
    group_name: str | None,
    chunk_types: list[str] | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
    section: str | None = None,
) -> tuple[str, dict[str, object]]:
    filters = []
    params: dict[str, object] = {}
    if textbook_ids:
        filters.append("tc.textbook_id = ANY(:textbook_ids)")
        params["textbook_ids"] = textbook_ids
    if group_name:
        filters.append("tb.group_name = :group_name")
        params["group_name"] = group_name
    if chunk_types:
        filters.append("tc.chunk_type = ANY(:chunk_types)")
        params["chunk_types"] = chunk_types
    if page_start is not None:
        filters.append("tc.page_start >= :page_start")
        params["page_start"] = page_start
    if page_end is not None:
        filters.append("tc.page_start <= :page_end")
        params["page_end"] = page_end
    if section:
        filters.append("tc.section = :section")
        params["section"] = section
    return (" AND ".join(filters) if filters else "TRUE"), params


def _dense_search(
    db: Session,
    query: str,
    textbook_ids: list[int] | None = None,
    group_name: str | None = None,
    chunk_types: list[str] | None = None,
    top_k: int = 20,
    page_start: int | None = None,
    page_end: int | None = None,
    section: str | None = None,
) -> list[dict]:
    where, params = _build_filters(textbook_ids, group_name, chunk_types, page_start, page_end, section)
    params["vector"] = embed_text(query, is_query=True)
    params["top_k"] = top_k

    rows = db.execute(text(f"""
        SELECT tc.id, tc.content, tc.chapter, tc.section, tc.chunk_type,
               tc.page_start, tc.page_end,
               tb.id AS textbook_id, tb.title AS textbook_title, tb.group_name,
               1.0 - (tc.embedding <=> CAST(:vector AS vector)) + COALESCE(0.02 * (1.0 - tc.page_start::float / NULLIF(tb.page_count, 0)), 0) AS score
        FROM text_chunks tc
        JOIN textbooks tb ON tb.id = tc.textbook_id
        WHERE {where}
        ORDER BY score DESC
        LIMIT :top_k
    """), params).mappings().all()
    return [dict(row) for row in rows]


def _sparse_search(
    db: Session,
    query: str,
    textbook_ids: list[int] | None = None,
    group_name: str | None = None,
    top_k: int = 20,
    page_start: int | None = None,
    page_end: int | None = None,
    section: str | None = None,
) -> list[dict]:
    where, params = _build_filters(textbook_ids, group_name, page_start=page_start, page_end=page_end, section=section)
    params["query"] = query
    params["top_k"] = top_k

    rows = db.execute(text(f"""
        SELECT tc.id, tc.content, tc.chapter, tc.section, tc.chunk_type,
               tc.page_start, tc.page_end,
               tb.id AS textbook_id, tb.title AS textbook_title, tb.group_name,
               ts_rank(to_tsvector('english', tc.content), plainto_tsquery('english', CAST(:query AS text))) AS score
        FROM text_chunks tc
        JOIN textbooks tb ON tb.id = tc.textbook_id
        WHERE {where}
          AND to_tsvector('english', tc.content) @@ plainto_tsquery('english', CAST(:query AS text))
        ORDER BY score DESC
        LIMIT :top_k
    """), params).mappings().all()
    return [dict(row) for row in rows]


def _rrf_fuse(result_sets: list[list[dict]], k: int = 60, top_k: int = 15) -> list[dict]:
    fused: dict[str, tuple[dict, float]] = {}
    for results in result_sets:
        for rank, doc in enumerate(results):
            doc_id = str(doc["id"])
            score = 1.0 / (k + rank + 1)
            if doc_id in fused:
                existing_doc, existing_score = fused[doc_id]
                fused[doc_id] = (existing_doc, existing_score + score)
            else:
                fused[doc_id] = (doc, score)

    output = []
    for doc, rrf_score in sorted(fused.values(), key=lambda x: x[1], reverse=True)[:top_k]:
        doc["score"] = rrf_score
        output.append(doc)
    return output


def hybrid_search(
    db: Session,
    query: str,
    textbook_ids: list[int] | None = None,
    group_name: str | None = None,
    top_k: int = 15,
    page_start: int | None = None,
    page_end: int | None = None,
    section: str | None = None,
) -> list[dict]:
    dense = _dense_search(db, query, textbook_ids, group_name, top_k=top_k, page_start=page_start, page_end=page_end, section=section)
    sparse = _sparse_search(db, query, textbook_ids, group_name, top_k=top_k, page_start=page_start, page_end=page_end, section=section)
    return _rrf_fuse([dense, sparse], k=60, top_k=top_k)


def get_context_chunks(
    db: Session,
    query: str,
    textbook_ids: list[int],
    group_name: str | None,
    chunk_types: list[str] | None = None,
    boost_equations: bool = False,
    page_start: int | None = None,
    page_end: int | None = None,
    section: str | None = None,
) -> list[dict]:
    fetch_k = max(settings.num_sources * settings.fetch_multiplier, settings.rerank_candidates)
    kwargs = dict(top_k=fetch_k, page_start=page_start, page_end=page_end, section=section)

    if settings.hybrid_search_enabled:
        results = hybrid_search(db, query, textbook_ids, group_name, **kwargs)
    else:
        results = _dense_search(db, query, textbook_ids, group_name, **kwargs)

    if chunk_types:
        results = [r for r in results if r.get("chunk_type") in chunk_types]
    if boost_equations:
        for r in results:
            if r.get("chunk_type") == "equation":
                r["score"] = r["score"] * 0.9
        results.sort(key=lambda x: x["score"], reverse=True)

    return results


def rewrite_query(raw_query: str) -> str:
    if not settings.query_rewrite_enabled:
        return raw_query

    import re
    query = re.sub(r"^\[Reading textbook.*?\]\s*", "", raw_query)
    query = re.sub(r"^(Create (a |)(flashcards|study guide)( covering each of these chapters)? for (these )?chapters:)", "", query)
    query = re.sub(r"^(Summarize (these )?chapters:)", "", query)
    query = re.sub(r"\d+\.\d+:\s*", "", query)
    query = re.sub(r"\s{2,}", " ", query)
    query = query.strip(" ,")

    if len(query.split()) < 3:
        return raw_query
    if not re.search(r"[?!.…]\s*$", query) and not any(v in query.lower() for v in ("what", "how", "why", "explain", "describe", "define", "compare", "find", "tell", "show")):
        return raw_query

    try:
        t0 = time.monotonic()
        rewritten, _ = llm_call(
            "You are a query rewriting assistant. Output only the rewritten query.",
            f"Rewrite this physics question into specific search terms with related concepts and standard physics terminology. Output ONLY the terms, no explanation:\n\nQuery: {query}",
            task="rewrite", max_tokens=128,
        )
        rewritten = rewritten.strip().strip('"').strip("'")
        elapsed = (time.monotonic() - t0) * 1000
        print(f"[LLM] rewrite | {elapsed:.0f}ms | '{query[:60]}' -> '{rewritten[:60]}'")
        return rewritten if (5 <= len(rewritten) <= len(raw_query) * 5) else raw_query
    except Exception:
        return raw_query


RERANK_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "score": {"type": "integer", "minimum": 1, "maximum": 5}},
                "required": ["id", "score"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["scores"],
    "additionalProperties": False,
}


def _remote_rerank(candidates: list[dict], query: str, top_k: int) -> list[dict] | None:
    client = get_rerank_client()
    if client is None or not settings.rerank_api_model:
        return None
    try:
        passages = [f"[{i}] ({c.get('textbook_title', '')} p.{c.get('page_start', '?')}) {c['content'][:500].replace(chr(10), ' ')}" for i, c in enumerate(candidates[:settings.rerank_candidates])]
        t0 = time.monotonic()
        resp = client.chat.completions.create(
            model=settings.rerank_api_model,
            messages=[{"role": "user", "content": f"Query: {query}\n\nScore each passage 1-5 for relevance to the query.\n\n" + "\n\n".join(passages)}],
            temperature=0.0, max_tokens=256,
            response_format={"type": "json_schema", "json_schema": {"name": "rerank", "schema": RERANK_SCHEMA}},
        )
        elapsed = (time.monotonic() - t0) * 1000
        data = json.loads(resp.choices[0].message.content or "{}")
        score_map = {item["id"]: item["score"] for item in data.get("scores", [])}
        if not score_map:
            print(f"[LLM] rerank returned empty scores, falling back to local")
            return None
        for i, c in enumerate(candidates[:settings.rerank_candidates]):
            c["rerank_score"] = score_map.get(i, 0)
        reranked = sorted(candidates[:settings.rerank_candidates], key=lambda x: x.get("rerank_score", 0), reverse=True)
        print(f"[LLM] rerank (remote) | {elapsed:.0f}ms | {len(candidates[:settings.rerank_candidates])} candidates")
        return reranked[:top_k]
    except Exception as e:
        print(f"[WARN] remote rerank failed: {e}")
        return None


_cross_encoder: object | None = None


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


def rerank_chunks(candidates: list[dict], query: str, top_k: int = 5) -> list[dict]:
    if not settings.rerank_enabled or len(candidates) <= top_k:
        return candidates[:top_k]

    result = _remote_rerank(candidates, query, top_k)
    if result is not None:
        return result

    try:
        model = _get_cross_encoder()
        pairs = [(query, c["content"][:500].replace("\n", " ")) for c in candidates[:settings.rerank_candidates]]
        scores = model.predict(pairs, show_progress_bar=False)
        for i, c in enumerate(candidates[:settings.rerank_candidates]):
            c["rerank_score"] = float(scores[i])
        return sorted(candidates[:settings.rerank_candidates], key=lambda x: x.get("rerank_score", 0), reverse=True)[:top_k]
    except Exception:
        return candidates[:top_k]
