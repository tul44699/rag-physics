"""End-to-end tests for the full RAG pipeline."""

import pytest

from models import ChatMessage, StudyEvent
from services import answer_query, build_user_profile
from prompts import get_task_instructions as task_instructions


class TestAnswerPipeline:
    """Test the full answer_query pipeline."""

    def test_answer_query_returns_answer_and_chunks(self, db, ingested_textbook):
        """Should return an answer string and a list of source chunks."""
        textbook_id, _ = ingested_textbook
        answer, chunks, parsed = answer_query(
            db=db,
            user_id="test-user",
            conversation_id="test-conv-1",
            prompt="What is Newton's first law?",
            task="qa",
            understanding_level="beginner",
            textbook_ids=[textbook_id],
            group_name=None,
        )
        assert isinstance(answer, str), "Answer should be a string"
        assert len(answer) > 20, f"Answer too short: '{answer}'"
        assert isinstance(chunks, list), "Chunks should be a list"
        assert len(chunks) > 0, "Should return at least one source chunk"

    def test_answer_references_newton(self, db, ingested_textbook):
        """Answer about Newton's laws should mention Newton or inertia."""
        textbook_id, _ = ingested_textbook
        answer, _, _ = answer_query(
            db=db,
            user_id="test-user",
            conversation_id="test-conv-2",
            prompt="Explain Newton's first law of motion",
            task="qa",
            understanding_level="beginner",
            textbook_ids=[textbook_id],
            group_name=None,
        )
        combined = answer.lower()
        assert "newton" in combined or "inertia" in combined or "force" in combined, (
            f"Answer doesn't mention Newton/inertia/force: {answer[:300]}"
        )

    def test_conversation_history_stored(self, db, ingested_textbook):
        """Messages should be saved to chat_messages table."""
        textbook_id, _ = ingested_textbook
        before = db.query(ChatMessage).count()
        answer_query(
            db=db,
            user_id="test-user",
            conversation_id="test-conv-3",
            prompt="What is F=ma?",
            task="qa",
            understanding_level="intermediate",
            textbook_ids=[textbook_id],
            group_name=None,
        )
        after = db.query(ChatMessage).count()
        assert after == before + 2, f"Expected 2 new messages, got {after - before}"

    def test_task_types_produce_different_responses(self, db, ingested_textbook):
        """Different task types should produce meaningfully different answers."""
        textbook_id, _ = ingested_textbook

        answers = {}
        for task in ["qa", "flashcards", "study_guide", "lookup"]:
            answer, _, _ = answer_query(
                db=db,
                user_id="test-user",
                conversation_id=f"test-conv-{task}",
                prompt="Newton's laws",
                task=task,
                understanding_level="intermediate",
                textbook_ids=[textbook_id],
                group_name=None,
            )
            answers[task] = answer

        # Flashcards should differ from qa
        assert answers["flashcards"] != answers["qa"], (
            "flashcards and qa should produce different responses"
        )
        # Lookup should be concise
        assert len(answers["lookup"]) < len(answers["study_guide"]) * 2, (
            "lookup should be more concise than study_guide"
        )


class TestProfileBuilding:
    """Test profile construction from study events."""

    def test_build_profile_with_events(self, db):
        """Profile should aggregate study events."""
        from models import StudyEvent, UserProfile

        profile = UserProfile(
            user_id="profile-test",
            profile_json={"understanding_level": "advanced"},
        )
        db.add(profile)
        for ch, mins, score in [
            ("Newton's Laws", 30, 0.9),
            ("Newton's Laws", 20, 0.85),
            ("Energy", 10, 0.4),
        ]:
            db.add(
                StudyEvent(
                    user_id="profile-test",
                    chapter=ch,
                    event_type="flashcard_generated",
                    minutes_spent=mins,
                    score=score,
                )
            )
        db.commit()

        result = build_user_profile(db, "profile-test")

        assert result["understanding_level"] == "advanced"
        assert "Energy" in result["weak_areas"]


class TestTaskInstructions:
    """Test task instruction generation."""

    def test_each_task_has_unique_instruction(self):
        """Every task type should have a distinct instruction."""
        tasks = ["qa", "lookup", "flashcards", "study_guide", "chapter_summary"]
        instructions = {t: task_instructions(t) for t in tasks}
        assert len(set(instructions.values())) == len(tasks), (
            "All task instructions should be unique"
        )

    def test_flashcards_mention_flashcards(self):
        assert "flashcard" in task_instructions("flashcards").lower()

    def test_study_guide_mentions_quiz(self):
        assert "practice questions" in task_instructions("study_guide").lower()
