from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    email: str
    display_name: str | None = None


class ProfileUpdateRequest(BaseModel):
    profile: dict = Field(default_factory=dict)


class StudyEventRequest(BaseModel):
    event_type: str
    chapter: str | None = None
    textbook_id: int | None = None
    minutes_spent: int = 0
    score: float | None = None


class IngestRequest(BaseModel):
    title: str
    pdf_path: str
    group_name: str | None = None
    chapter_hint: str | None = None
    chunk_size: int = 900
    chunk_overlap: int = 220


class SourceModel(BaseModel):
    textbook_id: int | None = None
    textbook: str
    chapter: str | None = None
    section: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    group_name: str | None = None
    chunk_type: str | None = None
    rerank_score: float | None = None
    snippet: str


class AskRequest(BaseModel):
    conversation_id: str
    prompt: str
    task: str = "qa"
    textbook_ids: list[int] = Field(default_factory=list)
    group_name: str | None = None
    understanding_level: str | None = None
    page_start: int | None = None
    page_end: int | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceModel]
    parsed: list | dict | None = None


class ChapterResponse(BaseModel):
    id: int
    textbook_id: int
    title: str
    page_start: int
    page_end: int | None = None


class TextbookResponse(BaseModel):
    id: int
    title: str
    group_name: str | None = None
    page_count: int | None = None
    chapter_count: int | None = None
    created_at: datetime


class TextbookDetailResponse(TextbookResponse):
    chapters: list[ChapterResponse] = []


class ChunkResponse(BaseModel):
    id: str
    chapter: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    content: str


class FormulaSheetItem(BaseModel):
    latex: str | None = None
    plain_text: str
    variables: list[str] = Field(default_factory=list)
    page_start: int | None = None
    section: str | None = None


class FormulaSheetResponse(BaseModel):
    sections: dict[str, dict[str, list[FormulaSheetItem]]]
    chapter_order: list[str]
    section_order: dict[str, list[str]]


class SearchResult(BaseModel):
    id: str
    chapter: str | None = None
    section: str | None = None
    chunk_type: str | None = None
    page_start: int | None = None
    snippet: str


class Anchor(BaseModel):
    type: str | None = None
    page: int | None = None
    chapter: str | None = None
    section: str | None = None
    label: str
    snippet: str


class ConceptResponse(BaseModel):
    id: int
    name: str
    description: str | None = None


class ConceptGraphResponse(BaseModel):
    concept: ConceptResponse
    relations: dict[str, list[ConceptResponse]]


class IngestResponse(BaseModel):
    textbook_id: int
    chunks_ingested: int


class OkResponse(BaseModel):
    ok: bool = True


class ProfileResponse(BaseModel):
    profile: dict
