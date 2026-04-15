import json as _json
import re
import shutil
import time
import uuid as _uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy.orm import Session
from classifier import classify_chunk, classify_query
from config import llm_call, settings
from embedding import embed_texts
from equations import extract_equations, retrieve_equations
from models import (
    Chapter,
    ChatMessage,
    Equation,
    StudyEvent,
    Textbook,
    TextChunk,
    UserProfile,
)
from prompts import (
    SYSTEM_PROMPT,
    build_profile_context,
    build_user_prompt,
)
from retrieval import get_context_chunks, rerank_chunks, rewrite_query

PDF_STORAGE = Path(__file__).parent / "pdfs"


def _log_llm(label: str, prompt: str, response: str, elapsed_ms: float) -> None:
    """Log an LLM call."""
    prompt_chars = len(prompt)
    resp_chars = len(response)
    preview = response[:200].replace("\n", "\\n")
    print(f"[LLM] {label} | {elapsed_ms:.0f}ms | prompt={prompt_chars}c | resp={resp_chars}c")
    print(f"[LLM] {label} preview: {preview}..." if len(response) > 200 else f"[LLM] {label} output: {preview}")


@dataclass
class PageDocument:
    """Minimal Document for langchain compatibility."""
    page_content: str
    metadata: dict


def _extract_pages(pdf_path: str, reader: PdfReader) -> list[PageDocument]:
    """Extract per-page text via LlamaParse."""
    if settings.llamaparse_api_key:
        return _extract_pages_llamaparse(pdf_path, reader)
    raise RuntimeError("LLAMAPARSE_API_KEY is required for PDF extraction")


def _extract_pages_llamaparse(pdf_path: str, reader: PdfReader) -> list[PageDocument]:
    """Extract per-page markdown via LlamaParse."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, _parse_with_llamaparse(pdf_path))
            return future.result()
    else:
        return asyncio.run(_parse_with_llamaparse(pdf_path))


async def _parse_with_llamaparse(pdf_path: str) -> list[PageDocument]:
    from llama_cloud_services import LlamaParse
    file_name = Path(pdf_path).name
    parser = LlamaParse(
        parse_mode="parse_page_with_agent",
        api_key=settings.llamaparse_api_key,
        result_type="markdown",
        show_progress=True,
        user_prompt="""\
Parse this physics textbook page into clean markdown.
CRITICAL: ALL math and equations MUST use proper LaTeX syntax with delimiters:
- Display equations: $$...$$ (e.g. $$F = ma$$)
- Inline math: \\(...\\) (e.g. \\(v_0 t + \\frac{1}{2} a t^2\\))
- Use _ for subscripts: v_0, x_i, F_{net}
- Use ^ for superscripts: v^2, x^{2}
- Use \\frac{num}{den} for fractions
- Use \\sqrt{x} for square roots
Preserve section headings as ## Markdown headings.
Omit page numbers, headers, and footers.""",
    )
    print(f"Calling LlamaParse API for {file_name} (this may take a few minutes)...")
    result = await parser.aparse(pdf_path)
    docs: list[PageDocument] = []
    for page in result.pages:
        page_num = page.page or 1
        content = page.md or page.text or ""
        docs.append(PageDocument(
            page_content=content,
            metadata={"page": page_num},
        ))
    print(f"LlamaParse returned {len(docs)} pages with proper page numbers")
    return docs


def _semantic_split(docs, chunk_size: int, chunk_overlap: int) -> list:
    """Structure-aware chunking with equation boundary awareness."""
    separators = [
        "\n\n## ",        # Markdown section headers
        "\n\n### ",       # Subsection headers
        "\n\n",           # Paragraphs
        "\n",             # Lines
        ". ",             # Sentences
        " ",              # Words
    ]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        length_function=len,
    )
    chunks = splitter.split_documents(docs)

    merged = []
    buffer = None
    for chunk in chunks:
        content = chunk.page_content
        max_size = settings.chunk_max_size

        if (
            merged
            and _is_equation_open(merged[-1].page_content)
            and not content.strip().startswith(("\\end", "$$", "\\]"))
            and len(merged[-1].page_content) + len(content) < max_size
        ):
            merged[-1].page_content += "\n" + content
            continue

        if len(content) < settings.chunk_min_size:
            if buffer is None:
                buffer = chunk
            else:
                buffer.page_content += "\n" + content
            continue

        if buffer is not None:
            combined = buffer.page_content + "\n" + content
            if len(combined) > max_size:
                merged.append(buffer)
                merged.append(chunk)
            else:
                buffer.page_content = combined
                merged.append(buffer)
            buffer = None
        else:
            merged.append(chunk)

    if buffer is not None:
        merged.append(buffer)
    return merged


def _is_equation_open(content: str) -> bool:
    """Check for unclosed LaTeX equation environment."""
    begins = content.count("\\begin{") + content.count("\\[")
    ends = content.count("\\end{") + content.count("\\]")
    if content.count("$$") % 2 != 0:
        return True
    return begins > ends


def _extract_section(content: str) -> str | None:
    """Extract section heading from chunk text."""
    first_line = content.split("\n")[0].strip()
    cleaned = re.sub(r"^#{1,3}\s*", "", first_line)
    for pattern in [
        r"^(\d+\.\d+(?:\.\d+)?[:\s].+)",     # "1.4: Newton's Laws" or "1.4 Title"
        r"^(Section\s+\d+\.\d+.*)",            # "Section 3.1"
        r"^(Chapter\s+\d+.*)",                 # "Chapter 5"
        r"^(Week\s+\d+.*)",                    # "Week 1: Newton's Laws"
    ]:
        m = re.match(pattern, cleaned, re.IGNORECASE)
        if m:
            return m.group(0).strip()[:255]
    return None


def _walk_outline(items: list, reader: PdfReader, depth: int = 0, max_depth: int = 2) -> list[dict]:
    """Walk PDF outline to collect chapter entries with page numbers."""
    entries: list[dict] = []
    for item in items:
        if isinstance(item, list):
            entries.extend(_walk_outline(item, reader, depth + 1, max_depth))
        elif hasattr(item, 'title') and hasattr(item, 'page') and depth <= max_depth:
            page_num = reader.get_page_number(item.page) + 1 if item.page else None
            entries.append({
                "title": str(item.title).strip(),
                "page_start": page_num or 1,
                "page_end": None,
            })
    return entries


def _is_chapter_title(title: str) -> bool:
    """Filter out noise entries from chapter outline."""
    skip_patterns = [
        r"^\s*(?:preface|foreword|acknowledgments?|copyright|front\s+cover|back\s+cover)\b",
        r"^\s*(?:contents?|bibliography|references?|glossary|index)\b",
        r"\bsummary\b",                      # "Summary", "Statics Summary", "Fluids Summary", etc.
        r"^\s*(?:homework\s+for)\b",        # "Homework for Week 1"
        r"^\s*(?:textbook\s+layout)\b",     # "Textbook Layout and Design"
        r"^\s*$",
    ]
    for pat in skip_patterns:
        if re.search(pat, title, re.IGNORECASE):
            return False
    return True


def _extract_chapters(pdf_path: str) -> list[dict]:
    try:
        reader = PdfReader(pdf_path)
        outline = reader.outline
        if not outline:
            return []

        all_entries = _walk_outline(outline, reader)
        chapters: list[dict] = []
        seen_titles: set[str] = set()
        for entry in all_entries:
            if not _is_chapter_title(entry["title"]):
                continue
            normalized = entry["title"].strip().lower()
            if normalized in seen_titles:
                continue
            seen_titles.add(normalized)
            chapters.append(entry)

        chapters.sort(key=lambda c: c["page_start"])
        for i in range(len(chapters) - 1):
            end = chapters[i + 1]["page_start"] - 1
            chapters[i]["page_end"] = max(chapters[i]["page_start"], end)
        if chapters:
            chapters[-1]["page_end"] = len(reader.pages)
        return chapters
    except Exception as e:
        print(f"Warning: failed to extract chapters from PDF outline: {e}")
        return []


def ingest_textbook(
    db: Session,
    title: str,
    pdf_path: str,
    group_name: str | None,
    chapter_hint: str | None,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[int, int]:
    PDF_STORAGE.mkdir(exist_ok=True)
    reader = PdfReader(pdf_path)
    page_count = len(reader.pages)

    textbook = Textbook(title=title, source_path=pdf_path, group_name=group_name, page_count=page_count)
    db.add(textbook)
    db.flush()

    dest = PDF_STORAGE / f"{textbook.id}.pdf"
    shutil.copy2(pdf_path, dest)
    textbook.source_path = str(dest)

    chapter_entries = _extract_chapters(pdf_path)
    for entry in chapter_entries:
        db.add(Chapter(textbook_id=textbook.id, **entry))
    textbook.chapter_count = len(chapter_entries)
    print(f"Detected {len(chapter_entries)} chapters, {page_count} pages")

    docs = _extract_pages(pdf_path, reader)

    if settings.semantic_chunking_enabled:
        chunks = _semantic_split(docs, chunk_size, chunk_overlap)
    else:
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = splitter.split_documents(docs)

    eq_data: list[dict] = []
    chunk_data: list[dict] = []
    chunk_texts: list[str] = []
    eq_texts: list[str] = []
    current_section = None

    for idx, item in enumerate(chunks):
        if idx % 200 == 0 and idx > 0:
            print(f"  Processed {idx}/{len(chunks)} chunks...")

        page = item.metadata.get("page")
        matched_chapter = _assign_chapter(page, chapter_entries)
        section = _extract_section(item.page_content)
        if section:
            current_section = section
        chunk_type = classify_chunk(item.page_content)
        chunk_id = _uuid.uuid4()
        chunk_data.append({
            "id": chunk_id,
            "textbook_id": textbook.id,
            "chapter": matched_chapter or chapter_hint,
            "section": current_section,
            "page_start": page,
            "page_end": page,
            "chunk_type": chunk_type,
            "content": item.page_content,
            "metadata_json": {"embedding_model": settings.embedding_api_model or settings.embedding_model},
        })
        chunk_texts.append(item.page_content)

        for eq in extract_equations(item.page_content):
            eq_data.append({
                "textbook_id": textbook.id,
                "chunk_id": chunk_id,
                "chapter": matched_chapter or chapter_hint,
                "section": current_section,
                "page_start": page,
                "latex": eq["latex"],
                "plain_text": eq["plain_text"],
                "variables": eq["variables"],
            })
            eq_texts.append(eq["plain_text"])

    print(f"Collected {len(chunk_data)} chunks and {len(eq_data)} equations")

    try:
        print("Embedding chunks...")
        chunk_vectors = embed_texts(chunk_texts, is_query=False)
        for cd, vec in zip(chunk_data, chunk_vectors):
            cd["embedding"] = vec

        eq_vectors: list[list[float]] = []
        if eq_texts:
            print("Embedding equations...")
            eq_vectors = embed_texts(eq_texts, is_query=False)

        for ed, vec in zip(eq_data, eq_vectors):
            ed["embedding"] = vec

        print("Inserting records...")
        db.add_all([TextChunk(**cd) for cd in chunk_data])
        if eq_data:
            db.add_all([Equation(**ed) for ed in eq_data])
        db.commit()
    except Exception:
        db.rollback()
        raise

    return textbook.id, len(chunk_data)


def _assign_chapter(page: int | None, chapter_entries: list[dict]) -> str | None:
    """Binary search to find which chapter owns a given page."""
    if page is None or not chapter_entries:
        return None

    target = page
    lo, hi = 0, len(chapter_entries)
    while lo < hi:
        mid = (lo + hi) // 2
        chapter_end = chapter_entries[mid].get("page_end")
        effective_end = chapter_end if chapter_end is not None else float("inf")
        if effective_end < target:
            lo = mid + 1
        else:
            hi = mid

    if lo < len(chapter_entries) and chapter_entries[lo]["page_start"] <= target:
        return chapter_entries[lo]["title"]
    return None


def build_user_profile(db: Session, user_id: str) -> dict:
    """Merge stored profile with derived stats from study events."""
    profile = db.get(UserProfile, user_id)
    base = dict(profile.profile_json) if profile else {}

    events = db.query(StudyEvent).filter(StudyEvent.user_id == user_id).all()
    chapter_scores: dict[str, list[float]] = defaultdict(list)
    for event in events:
        if event.score is not None and event.chapter:
            chapter_scores[event.chapter].append(event.score)

    weaknesses: list[tuple[str, float]] = []
    for ch_name, ch_scores in chapter_scores.items():
        avg = sum(ch_scores) / len(ch_scores)
        if avg < 0.5:
            weaknesses.append((ch_name, avg))

    if weaknesses:
        weaknesses.sort(key=lambda x: x[1])
        base["weak_areas"] = [ch for ch, _ in weaknesses[:3]]

    return base


FLASHCARD_SCHEMA = {
    "type": "array",
    "minItems": 6,
    "maxItems": 6,
    "items": {
        "type": "object",
        "properties": {
            "front": {"type": "string"},
            "back": {"type": "string"},
            "source_n": {"type": "integer", "minimum": 1},
        },
        "required": ["front", "back", "source_n"],
        "additionalProperties": False,
    },
}

STUDY_GUIDE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "key_concepts": {
            "type": "array",
            "items": {"type": "string"},
        },
        "key_equations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "equation": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["equation", "description"],
                "additionalProperties": False,
            },
        },
        "common_mistakes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "practice_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                },
                "required": ["question", "answer"],
                "additionalProperties": False,
            },
        },
        "sources": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["title", "key_concepts", "key_equations", "common_mistakes", "sources"],
    "additionalProperties": False,
}

CHAPTER_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "chapter_name": {"type": "string"},
        "core_concepts": {
            "type": "array",
            "items": {"type": "string"},
        },
        "essential_formulas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "formula": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["formula", "description"],
                "additionalProperties": False,
            },
        },
        "common_mistakes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "sources": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["chapter_name", "core_concepts", "essential_formulas", "common_mistakes", "sources"],
    "additionalProperties": False,
}

TASK_SCHEMAS: dict[str, dict] = {
    "flashcards": FLASHCARD_SCHEMA,
    "study_guide": STUDY_GUIDE_SCHEMA,
    "chapter_summary": CHAPTER_SUMMARY_SCHEMA,
}


def _render_structured_markdown(task: str, data: dict | list) -> str:
    """Convert structured JSON to markdown."""
    if task == "study_guide":
        if isinstance(data, dict):
            return _render_study_guide(data)
    elif task == "chapter_summary":
        if isinstance(data, dict):
            return _render_chapter_summary(data)
    elif task == "flashcards":
        if isinstance(data, list):
            return _render_flashcards_md(data)
    return ""


def _render_study_guide(d: dict) -> str:
    lines = [f"## {d.get('title', 'Study Guide')}"]
    lines.append("\n### Key Concepts")
    for c in d.get("key_concepts", []):
        lines.append(f"- {c}")
    lines.append("\n### Key Equations")
    for eq in d.get("key_equations", []):
        lines.append(f"- **{eq['equation']}**: {eq['description']}")
    lines.append("\n### Common Mistakes")
    for m in d.get("common_mistakes", []):
        lines.append(f"- {m}")
    if d.get("practice_questions"):
        lines.append("\n### Practice Questions")
        for i, pq in enumerate(d["practice_questions"], 1):
            lines.append(f"{i}. {pq['question']}")
            lines.append(f"   **Answer:** {pq['answer']}")
    lines.append("\n## Sources")
    for s in d.get("sources", []):
        lines.append(s)
    return "\n".join(lines)


def _render_chapter_summary(d: dict) -> str:
    lines = [f"## Chapter Summary: {d.get('chapter_name', '')}"]
    lines.append("\n### Core Concepts")
    for c in d.get("core_concepts", []):
        lines.append(f"- {c}")
    lines.append("\n### Essential Formulas")
    for eq in d.get("essential_formulas", []):
        lines.append(f"- **{eq['formula']}**: {eq['description']}")
    lines.append("\n### Common Mistakes")
    for m in d.get("common_mistakes", []):
        lines.append(f"- {m}")
    lines.append("\n## Sources")
    for s in d.get("sources", []):
        lines.append(s)
    return "\n".join(lines)


def _extract_referenced_sources(chunks: list[dict], parsed: list | dict | None, task: str, answer: str) -> list[dict]:
    """Filter chunks to only those referenced in the output."""
    if not chunks:
        return chunks

    refs: set[int] = set()
    if task == "flashcards" and isinstance(parsed, list):
        for card in parsed:
            n = card.get("source_n")
            if isinstance(n, int) and 1 <= n <= len(chunks):
                refs.add(n - 1)
    elif task in ("study_guide", "chapter_summary") and isinstance(parsed, dict):
        for n in parsed.get("sources", []):
            n = _parse_citation_number(n) if isinstance(n, str) else n
            if isinstance(n, int) and 1 <= n <= len(chunks):
                refs.add(n - 1)

    # For free-text tasks: parse [N] citations from the answer
    if not refs and answer:
        for m in re.finditer(r"\[(\d+)\]", answer):
            n = int(m.group(1))
            if 1 <= n <= len(chunks):
                refs.add(n - 1)

    if not refs:
        return chunks
    return [chunks[i] for i in sorted(refs)]


def _parse_citation_number(s: str) -> int | None:
    m = re.match(r"\[(\d+)\]", s)
    return int(m.group(1)) if m else None


def _render_flashcards_md(data: list) -> str:
    lines = ["## Flashcards"]
    for i, card in enumerate(data, 1):
        lines.append(f"\n**Q{i}:** {card['front']}")
        lines.append(f"**A{i}:** {card['back']}")
    return "\n".join(lines)


def _retrieve_and_build_prompt(
    db: Session,
    user_id: str,
    conversation_id: str,
    prompt: str,
    task: str,
    understanding_level: str | None,
    textbook_ids: list[int],
    group_name: str | None,
    page_start: int | None,
    page_end: int | None,
) -> tuple[str, str | None, list[dict] | None]:
    """Retrieve chunks and build prompts. Returns (system_prompt, user_prompt, chunks) or (fallback_msg, None, None)."""
    profile = build_user_profile(db, user_id)
    qc = classify_query(prompt)
    search_query = rewrite_query(prompt)

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id, ChatMessage.user_id == user_id)
        .order_by(ChatMessage.id.desc()).limit(4).all()
    )
    history = list(reversed(history))

    # Auto-detect follow-ups: short prompt with existing history → conversational mode
    if history and len(prompt.strip().split()) < 15:
        q_words = ("what", "how", "why", "explain", "describe", "define", "compare", "create", "generate", "summarize", "make", "find")
        if not any(prompt.strip().lower().startswith(w) for w in q_words):
            task = "follow_up"

    chunk_types = None
    if qc.get("is_math_query"):
        chunk_types = ["equation", "definition"]
    elif qc.get("is_definition_query"):
        chunk_types = ["definition"]
    elif qc.get("is_derivation_query"):
        chunk_types = ["derivation"]

    candidates = get_context_chunks(
        db, search_query, textbook_ids, group_name,
        boost_equations=qc["is_math_query"],
        chunk_types=chunk_types,
        page_start=page_start, page_end=page_end,
    )
    chunks = rerank_chunks(candidates, prompt, top_k=settings.num_sources)

    if settings.min_source_score > 0 and any("rerank_score" in c for c in chunks):
        chunks = [c for c in chunks if c.get("rerank_score", 0) >= settings.min_source_score]
    chunks = chunks[:settings.num_sources]

    if not chunks:
        fallback = "I couldn't find relevant material in the textbook to answer this question. Try rephrasing or broadening your search."
        db.add(ChatMessage(conversation_id=conversation_id, user_id=user_id, role="user", task=task, content=prompt))
        db.add(ChatMessage(conversation_id=conversation_id, user_id=user_id, role="assistant", task=task, content=fallback))
        db.commit()
        return fallback, None, None

    eq_context = ""
    if qc["is_math_query"]:
        eq_results = retrieve_equations(db, search_query, textbook_ids, top_k=3)
        if eq_results:
            eq_context = "\n\nRelevant equations:\n" + "\n".join(
                f"[Eq {i + 1}] {eq.get('plain_text')} ({eq.get('textbook_title')} p.{eq.get('page_start')})"
                for i, eq in enumerate(eq_results)
            )

    context_parts = []
    for idx, chunk in enumerate(chunks):
        ctype = f" [{chunk.get('chunk_type', 'text')}]" if chunk.get("chunk_type") else ""
        section_info = f" §{chunk.get('section')}" if chunk.get("section") else ""
        context_parts.append(
            f"[{idx + 1}]{ctype}{section_info} {chunk['textbook_title']} p.{chunk.get('page_start')}: {chunk['content'][:3000]}"
        )
    context = "\n\n".join(context_parts)

    history_text = "\n".join([f"{item.role}: {item.content}" for item in history])

    system_prompt = SYSTEM_PROMPT.format(
        profile_context=build_profile_context(profile, understanding_level)
    )
    user_prompt = build_user_prompt(
        prompt=prompt, task=task, context=context,
        eq_context=eq_context, history_text=history_text,
    )
    return system_prompt, user_prompt, chunks


def _parse_and_render(answer: str, task: str) -> tuple[dict | list | None, str]:
    """Parse JSON answer and render to markdown. Returns (parsed, display_content)."""
    if not answer.strip():
        return None, answer
    json_schema = TASK_SCHEMAS.get(task)
    if json_schema is None:
        return None, answer
    try:
        parsed = _json.loads(answer)
        rendered = _render_structured_markdown(task, parsed)
        return parsed, rendered if rendered.strip() else answer
    except (_json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"[WARN] failed to parse/format {task}: {e}")
        return None, answer


def best_excerpt(content: str, query: str, max_len: int = 240) -> str:
    if len(content) <= max_len:
        return content
    query_terms = set(query.lower().split())
    best_start = 0
    best_score = 0
    for i in range(0, len(content) - max_len, 40):
        window = content[i:i + max_len].lower()
        score = sum(1 for t in query_terms if t in window)
        if score > best_score:
            best_score = score
            best_start = i
    start = best_start
    if start > 0:
        prev_period = content.rfind(". ", 0, start)
        if prev_period > 0:
            start = prev_period + 2
    return content[start:start + max_len].strip()


def _source_list(chunks: list[dict], query: str = "") -> list[dict]:
    return [
        {
            "textbook_id": s.get("textbook_id"), "textbook": s["textbook_title"],
            "chapter": s.get("chapter"), "section": s.get("section"),
            "page_start": s.get("page_start"), "page_end": s.get("page_end"),
            "group_name": s.get("group_name"), "chunk_type": s.get("chunk_type"),
            "rerank_score": s.get("rerank_score"),
            "snippet": best_excerpt(s["content"], query),
        }
        for s in chunks
    ]


def answer_query(
    db: Session,
    user_id: str,
    conversation_id: str,
    prompt: str,
    task: str,
    understanding_level: str | None,
    textbook_ids: list[int],
    group_name: str | None,
    page_start: int | None = None,
    page_end: int | None = None,
) -> tuple[str, list[dict], list | dict | None]:
    system_prompt, user_prompt, chunks = _retrieve_and_build_prompt(
        db, user_id, conversation_id, prompt, task, understanding_level,
        textbook_ids, group_name, page_start, page_end,
    )
    if user_prompt is None:
        return system_prompt, [], None  # fallback message

    t0 = time.monotonic()
    json_schema = TASK_SCHEMAS.get(task)
    answer, think = llm_call(system_prompt, user_prompt, json_schema=json_schema, json_schema_name=task)
    _log_llm(f"answer ({task})", system_prompt + "\n" + user_prompt, answer, (time.monotonic() - t0) * 1000)

    parsed, display_content = _parse_and_render(answer, task)
    if json_schema is not None and not answer.strip():
        print(f"[WARN] LLM returned empty answer for task={task}")
        display_content = "I couldn't generate a response. Please try again."

    db.add(ChatMessage(conversation_id=conversation_id, user_id=user_id, role="user", task=task, content=prompt))
    db.add(ChatMessage(conversation_id=conversation_id, user_id=user_id, role="assistant", task=task, content=display_content))
    db.commit()

    sources = _extract_referenced_sources(chunks, parsed, task, display_content)
    return display_content, sources, parsed


def answer_query_stream(
    db: Session,
    user_id: str,
    conversation_id: str,
    prompt: str,
    task: str,
    understanding_level: str | None,
    textbook_ids: list[int],
    group_name: str | None,
    page_start: int | None = None,
    page_end: int | None = None,
):

    system_prompt, user_prompt, chunks = _retrieve_and_build_prompt(
        db, user_id, conversation_id, prompt, task, understanding_level,
        textbook_ids, group_name, page_start, page_end,
    )
    if user_prompt is None:
        yield f"data: {_json.dumps({'token': system_prompt})}\n\n"
        yield f"data: {_json.dumps({'done': True, 'sources': [], 'parsed': None})}\n\n"
        return

    raw = ""
    t0 = time.monotonic()
    for token in llm_call(system_prompt, user_prompt, json_schema=TASK_SCHEMAS.get(task), json_schema_name=task, stream=True):
        raw += token
        yield f"data: {_json.dumps({'token': token})}\n\n"

    elapsed = (time.monotonic() - t0) * 1000
    print(f"[LLM] answer ({task}) stream | {elapsed:.0f}ms | resp={len(raw)}c")

    parsed, display_content = _parse_and_render(raw, task)
    sources = _extract_referenced_sources(chunks, parsed, task, display_content)
    yield f"data: {_json.dumps({'done': True, 'sources': _source_list(sources, prompt), 'parsed': parsed, 'display_content': display_content})}\n\n"

    db.add(ChatMessage(conversation_id=conversation_id, user_id=user_id, role="user", task=task, content=prompt))
    db.add(ChatMessage(conversation_id=conversation_id, user_id=user_id, role="assistant", task=task, content=display_content))
    db.commit()
