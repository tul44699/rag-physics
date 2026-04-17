import pytest
from prompts import SYSTEM_PROMPT, TASK_INSTRUCTIONS, build_profile_context, build_system_prompt, build_user_prompt, get_task_instructions
from services import FLASHCARD_SCHEMA, TASK_SCHEMAS, _extract_referenced_sources, _parse_and_render, _render_structured_markdown
from retrieval import _rrf_fuse, _dense_search, _sparse_search, hybrid_search, get_context_chunks
from embedding import embed_text
from config import settings


class TestPrompts:
    def test_system_prompt_has_rules(self):
        assert "{profile_context}" in SYSTEM_PROMPT
        assert "physics tutor" in SYSTEM_PROMPT.lower()
        assert "\\sqrt" in SYSTEM_PROMPT
        assert "\\rho" in SYSTEM_PROMPT

    def test_profile_context(self):
        profile = {"understanding_level": "beginner", "course": "Physics 101", "weak_areas": ["Energy"]}
        result = build_profile_context(profile)
        assert "beginner" in result
        assert "Physics 101" in result
        assert "Energy" in result

    def test_build_system_prompt(self):
        result = build_system_prompt({"understanding_level": "advanced"}, "beginner")
        assert "advanced" in result or "beginner" in result

    def test_all_tasks_exist(self):
        for task in ["qa", "lookup", "flashcards", "study_guide", "chapter_summary", "follow_up"]:
            assert task in TASK_INSTRUCTIONS
            assert isinstance(TASK_INSTRUCTIONS[task], str)

    def test_fallback_to_qa(self):
        assert get_task_instructions("unknown") == get_task_instructions("qa")

    def test_user_prompt_structure(self):
        result = build_user_prompt(prompt="test", task="qa", context="[1] p.1: text", eq_context="[Eq 1] F=ma", history_text="user: hi\nassistant: hello")
        assert "## Task" in result
        assert "## Source Material" in result
        assert "## Question" in result
        assert result.strip().endswith("test")

    def test_user_prompt_history(self):
        with_history = build_user_prompt(prompt="t", task="qa", context="c", eq_context="", history_text="u: hi\na: hey")
        without_history = build_user_prompt(prompt="t", task="qa", context="c", eq_context="", history_text="")
        assert "## Conversation" in with_history
        assert "Conversation" not in without_history


class TestEmbedding:
    def test_embedding_dimensions(self):
        vec = embed_text("test", is_query=False)
        assert len(vec) == settings.embedding_dim

    def test_query_vs_doc(self):
        if settings.embedding_base_url:
            pytest.skip("remote embedding may not differentiate query/doc")
        assert embed_text("test", is_query=True) != embed_text("test", is_query=False)


class TestRetrieval:
    def test_dense_search(self, db, ingested_textbook):
        results = _dense_search(db, "Newton's laws", None, None, top_k=5)
        assert len(results) > 0
        assert all("content" in r for r in results)

    def test_sparse_search(self, db, ingested_textbook):
        assert len(_sparse_search(db, "Newton's laws", None, None, top_k=5)) > 0

    def test_hybrid_search(self, db, ingested_textbook):
        if not settings.hybrid_search_enabled:
            pytest.skip("disabled")
        assert len(hybrid_search(db, "Newton's laws", None, None, top_k=5)) > 0

    def test_rrf_fusion(self):
        shared = "s1"
        a = [{"id": shared, "content": "x", "score": 0.9}, {"id": "a2", "content": "y", "score": 0.8}]
        b = [{"id": "b1", "content": "z", "score": 0.9}, {"id": shared, "content": "x", "score": 0.5}]
        assert _rrf_fuse([a, b], k=60, top_k=3)[0]["id"] == shared

    def test_textbook_filtering(self, db, ingested_textbook):
        tid, _ = ingested_textbook
        assert len(get_context_chunks(db, "Newton", [tid], None)) > 0
        assert len(get_context_chunks(db, "Newton", [99999], None)) == 0

    def test_page_numbers_present(self, db, ingested_textbook):
        for chunk in get_context_chunks(db, "Newton", [], None):
            assert chunk.get("page_start") is not None


class TestServices:
    def test_flashcard_schema(self):
        assert FLASHCARD_SCHEMA["minItems"] == 6
        assert FLASHCARD_SCHEMA["maxItems"] == 6
        assert "source_n" in FLASHCARD_SCHEMA["items"]["required"]

    def test_task_schemas_registered(self):
        for t in ["flashcards", "study_guide", "chapter_summary"]:
            assert t in TASK_SCHEMAS

    def test_parse_and_render_flashcards(self):
        parsed, rendered = _parse_and_render('[{"front":"Q?","back":"A","source_n":1}]', "flashcards")
        assert len(parsed) == 1
        assert "Q1" in rendered
        assert "A" in rendered

    def test_parse_invalid_json(self):
        parsed, rendered = _parse_and_render("not json", "flashcards")
        assert parsed is None
        assert rendered == "not json"

    def test_render_unknown_task(self):
        assert _render_structured_markdown("unknown", {}) == ""

    def test_extract_referenced_sources(self):
        chunks = [{"id": f"c{i}", "textbook_title": "T", "content": "x", "page_start": i+1} for i in range(3)]
        result = _extract_referenced_sources(chunks, None, "qa", "See [1] and [3]")
        assert len(result) == 2
        assert result[0]["id"] == "c0"
        assert result[1]["id"] == "c2"

    def test_no_citations_returns_all(self):
        chunks = [{"id": "c0", "textbook_title": "T", "content": "x", "page_start": 1}]
        assert len(_extract_referenced_sources(chunks, None, "qa", "no refs")) == 1
