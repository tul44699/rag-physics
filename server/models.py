import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text

from config import settings
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    textbook_id: Mapped[int] = mapped_column(ForeignKey("textbooks.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    textbook: Mapped["Textbook"] = relationship(back_populates="chapters")


class Textbook(Base):
    __tablename__ = "textbooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    source_path: Mapped[str] = mapped_column(String(1000))
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chapter_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    chapters: Mapped[list["Chapter"]] = relationship(back_populates="textbook")
    chunks: Mapped[list["TextChunk"]] = relationship(back_populates="textbook")


class TextChunk(Base):
    __tablename__ = "text_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    textbook_id: Mapped[int] = mapped_column(ForeignKey("textbooks.id"), index=True)
    chapter: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))

    textbook: Mapped[Textbook] = relationship(back_populates="chunks")
    equations: Mapped[list["Equation"]] = relationship(back_populates="chunk")


class Equation(Base):
    __tablename__ = "equations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    textbook_id: Mapped[int] = mapped_column(ForeignKey("textbooks.id"), index=True)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("text_chunks.id"), nullable=True)
    chapter: Mapped[str | None] = mapped_column(String(255), nullable=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latex: Mapped[str | None] = mapped_column(Text, nullable=True)
    plain_text: Mapped[str] = mapped_column(Text)
    variables: Mapped[list] = mapped_column(JSON, default=list)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))

    textbook: Mapped["Textbook"] = relationship()
    chunk: Mapped["TextChunk"] = relationship(back_populates="equations")


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    textbook_id: Mapped[int] = mapped_column(ForeignKey("textbooks.id"), index=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim))

    textbook: Mapped["Textbook"] = relationship()


class ConceptRelation(Base):
    __tablename__ = "concept_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(50))


class ConceptChunk(Base):
    __tablename__ = "concept_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id"), index=True)
    chunk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("text_chunks.id"), index=True)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    profile_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class StudyEvent(Base):
    __tablename__ = "study_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    textbook_id: Mapped[int | None] = mapped_column(ForeignKey("textbooks.id"), nullable=True, index=True)
    chapter: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    minutes_spent: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(120), index=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    role: Mapped[str] = mapped_column(String(20))
    task: Mapped[str] = mapped_column(String(50), default="qa")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
