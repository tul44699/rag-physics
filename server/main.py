import json as _json
from collections import defaultdict
from pathlib import Path

from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, hash_password, verify_password
from config import llm_call
from db import Base, engine, get_db
from embedding import embed_text
from models import (
    Chapter, Concept, ConceptChunk, ConceptRelation,
    Equation, StudyEvent, TextChunk, Textbook, User, UserProfile,
)
from schemas import (
    Anchor, AskRequest, AskResponse, AuthResponse, ChunkResponse,
    ConceptResponse, ConceptGraphResponse, FormulaSheetItem,
    FormulaSheetResponse, IngestRequest, IngestResponse, LoginRequest,
    OkResponse, ProfileResponse, ProfileUpdateRequest, RegisterRequest,
    SearchResult, SourceModel, StudyEventRequest,
    TextbookDetailResponse, TextbookResponse,
)
from services import answer_query, best_excerpt, build_user_profile, ingest_textbook

app = FastAPI(title="Physics RAG")

CLIENT_DIST = Path(__file__).parent.parent / "client" / "dist"
if CLIENT_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=CLIENT_DIST / "assets"), name="client_assets")


@app.on_event("startup")
def startup() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    Base.metadata.create_all(bind=engine)


@app.get("/")
async def root():
    if (CLIENT_DIST / "index.html").is_file():
        return FileResponse(CLIENT_DIST / "index.html")
    return {"message": "Physics RAG API"}


# ── Auth ──

@app.post("/api/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=payload.email, hashed_password=hash_password(payload.password), display_name=payload.display_name)
    db.add(user); db.commit(); db.refresh(user)
    token = create_access_token({"sub": str(user.id), "email": user.email, "display_name": user.display_name})
    return AuthResponse(token=token, user_id=user.id, email=user.email, display_name=user.display_name)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id), "email": user.email, "display_name": user.display_name})
    return AuthResponse(token=token, user_id=user.id, email=user.email, display_name=user.display_name)


# ── Profile ──

@app.put("/api/profile", response_model=OkResponse)
def update_profile(payload: ProfileUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.get(UserProfile, str(current_user.id))
    if profile is None:
        db.add(UserProfile(user_id=str(current_user.id), profile_json=payload.profile))
    else:
        profile.profile_json = payload.profile
    db.commit()
    return {"ok": True}


@app.get("/api/profile", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"profile": build_user_profile(db, str(current_user.id))}


# ── Events ──

@app.post("/api/events", response_model=OkResponse)
def create_event(payload: StudyEventRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.add(StudyEvent(user_id=str(current_user.id), **payload.model_dump()))
    db.commit()
    return {"ok": True}


# ── Textbooks ──

@app.get("/api/textbooks", response_model=list[TextbookResponse])
def list_textbooks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Textbook).order_by(Textbook.created_at.desc()).all()


@app.get("/api/textbooks/{textbook_id}", response_model=TextbookDetailResponse)
def get_textbook(textbook_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tb = db.get(Textbook, textbook_id)
    if not tb: raise HTTPException(status_code=404, detail="Textbook not found")
    return tb


@app.get("/api/textbooks/{textbook_id}/pdf")
def get_textbook_pdf(textbook_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tb = db.get(Textbook, textbook_id)
    if not tb: raise HTTPException(status_code=404, detail="Textbook not found")
    path = Path(tb.source_path)
    if not path.is_file(): raise HTTPException(status_code=404, detail="PDF file not found")
    return FileResponse(str(path), media_type="application/pdf")


@app.get("/api/textbooks/{textbook_id}/chunks", response_model=list[ChunkResponse])
def get_textbook_chunks(
    textbook_id: int,
    chapter: str | None = Query(default=None),
    page: int | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(TextChunk).filter(TextChunk.textbook_id == textbook_id)
    if chapter: q = q.filter(TextChunk.chapter == chapter)
    if page is not None: q = q.filter(TextChunk.page_start <= page, TextChunk.page_end >= page)
    return q.limit(limit).all()


@app.delete("/api/textbooks/{textbook_id}", response_model=OkResponse)
def delete_textbook(textbook_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tb = db.get(Textbook, textbook_id)
    if not tb: raise HTTPException(status_code=404, detail="Textbook not found")
    path = Path(tb.source_path)
    if path.is_file(): path.unlink()
    db.query(TextChunk).filter(TextChunk.textbook_id == textbook_id).delete()
    db.query(Chapter).filter(Chapter.textbook_id == textbook_id).delete()
    db.delete(tb); db.commit()
    return {"ok": True}


# ── Ingestion ──

@app.post("/api/ingest/textbook", response_model=IngestResponse)
def ingest(payload: IngestRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        textbook_id, chunk_count = ingest_textbook(
            db=db, title=payload.title, pdf_path=payload.pdf_path,
            group_name=payload.group_name, chapter_hint=payload.chapter_hint,
            chunk_size=payload.chunk_size, chunk_overlap=payload.chunk_overlap,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"PDF not found: {exc}") from exc
    return {"textbook_id": textbook_id, "chunks_ingested": chunk_count}


# ── Navigation ──

@app.get("/api/textbooks/{textbook_id}/anchors", response_model=list[Anchor])
def get_textbook_anchors(textbook_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chunks = db.query(TextChunk).filter(TextChunk.textbook_id == textbook_id, TextChunk.chunk_type != None).all()
    eqs = db.query(Equation).filter(Equation.textbook_id == textbook_id).all()
    anchors = []
    for c in chunks:
        label = c.content[:80].replace("\n", " ")
        anchors.append(Anchor(type=c.chunk_type, page=c.page_start, chapter=c.chapter, section=c.section, label=f"[{c.chunk_type}] {label}...", snippet=c.content[:200]))
    for eq in eqs:
        anchors.append(Anchor(type="equation", page=eq.page_start, chapter=eq.chapter, label=eq.plain_text[:80], snippet=eq.plain_text))
    return anchors


@app.get("/api/textbooks/{textbook_id}/search", response_model=list[SearchResult])
def search_textbook(
    textbook_id: int, q: str = Query(...), limit: int = Query(default=10, le=50),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    results = db.query(TextChunk).filter(
        TextChunk.textbook_id == textbook_id,
        or_(TextChunk.content.ilike(f"%{q}%"), TextChunk.chapter.ilike(f"%{q}%")),
    ).limit(limit).all()
    return [SearchResult(id=str(r.id), chapter=r.chapter, section=r.section, chunk_type=r.chunk_type, page_start=r.page_start, snippet=r.content[:200]) for r in results]


# ── Formula Sheet ──

_NOISE_PREFIXES = ("PROBLEMS", "QUESTIONS", "Cover", "Title Page", "Copyright", "Contents", "PREFACE", "ANSWERS")


@app.post("/api/formulasheet", response_model=FormulaSheetResponse)
def generate_formula_sheet(
    textbook_ids: list[int] = Body(default=[]),
    chapter: str | None = Body(default=None),
    page_start: int | None = Body(default=None),
    page_end: int | None = Body(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Equation)
    if textbook_ids: q = q.filter(Equation.textbook_id.in_(textbook_ids))
    if chapter: q = q.filter(Equation.chapter.ilike(f"%{chapter}%"))
    if page_start is not None: q = q.filter(Equation.page_start >= page_start)
    if page_end is not None: q = q.filter(Equation.page_start <= page_end)

    chapters: dict[str, dict[str, list[FormulaSheetItem]]] = {}
    chapter_order: list[str] = []
    section_order: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()

    for eq in q.order_by(Equation.page_start).all():
        ch = eq.chapter or "General"
        if ch.startswith(_NOISE_PREFIXES): continue
        sec = eq.section or "General"
        key = (ch, eq.plain_text)
        if key in seen: continue
        seen.add(key)
        if ch not in chapters:
            chapters[ch] = {}; chapter_order.append(ch); section_order[ch] = []
        if sec not in chapters[ch]:
            chapters[ch][sec] = []; section_order[ch].append(sec)
        chapters[ch][sec].append(FormulaSheetItem(latex=eq.latex, plain_text=eq.plain_text, variables=eq.variables, page_start=eq.page_start, section=eq.section))

    return FormulaSheetResponse(sections=chapters, chapter_order=chapter_order, section_order=section_order)


# ── Concepts ──

CONCEPT_SCHEMA = {
    "type": "object",
    "properties": {
        "concepts": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}}, "required": ["name", "description"], "additionalProperties": False}},
        "relations": {"type": "array", "items": {"type": "object", "properties": {"source": {"type": "string"}, "target": {"type": "string"}, "type": {"type": "string", "enum": ["prerequisite", "derives", "applies_to", "related"]}}, "required": ["source", "target", "type"], "additionalProperties": False}},
    },
    "required": ["concepts", "relations"], "additionalProperties": False,
}

CONCEPT_SYSTEM = "Extract physics concepts and relationships. Concept names must be short and canonical. Every source and target in relations must appear in concepts. Omit relations if none are clearly implied."


@app.post("/api/concepts/build")
def build_concept_graph(textbook_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(ConceptRelation).filter(ConceptRelation.source_id.in_(db.query(Concept.id).filter(Concept.textbook_id == textbook_id))).delete(synchronize_session=False)
    db.query(ConceptChunk).filter(ConceptChunk.concept_id.in_(db.query(Concept.id).filter(Concept.textbook_id == textbook_id))).delete(synchronize_session=False)
    db.query(Concept).filter(Concept.textbook_id == textbook_id).delete(synchronize_session=False)
    db.commit()

    chunks = db.query(TextChunk).filter(TextChunk.textbook_id == textbook_id).all()
    if not chunks: return {"concepts": 0}

    all_text = "\n".join([c.content[:500] for c in chunks[:20]])
    raw, _ = llm_call(system=CONCEPT_SYSTEM, user=all_text[:8000], task="general", max_tokens=2048, json_schema=CONCEPT_SCHEMA, json_schema_name="concepts")
    data = _json.loads(raw)

    name_to_id: dict[str, int] = {}
    for c in data.get("concepts", []):
        obj = Concept(name=c["name"], description=c.get("description", ""), textbook_id=textbook_id, embedding=embed_text(c["name"] + " " + c.get("description", "")))
        db.add(obj); db.flush()
        name_to_id[c["name"]] = obj.id

    for r in data.get("relations", []):
        src, tgt = name_to_id.get(r["source"]), name_to_id.get(r["target"])
        if src and tgt: db.add(ConceptRelation(source_id=src, target_id=tgt, relation_type=r["type"]))

    db.commit()
    return {"concepts": len(name_to_id)}


@app.get("/api/concepts/search", response_model=list[ConceptResponse])
def search_concepts(q: str = Query(...), textbook_id: int | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    qs = db.query(Concept).filter(Concept.name.ilike(f"%{q}%") | Concept.description.ilike(f"%{q}%"))
    if textbook_id: qs = qs.filter(Concept.textbook_id == textbook_id)
    return [ConceptResponse(id=r.id, name=r.name, description=r.description) for r in qs.limit(10).all()]


@app.get("/api/concepts/{concept_id}/graph", response_model=ConceptGraphResponse)
def get_concept_graph(concept_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.get(Concept, concept_id)
    if not c: raise HTTPException(status_code=404, detail="Concept not found")
    rels = db.query(ConceptRelation).filter((ConceptRelation.source_id == concept_id) | (ConceptRelation.target_id == concept_id)).all()
    related: dict[str, list[ConceptResponse]] = defaultdict(list)
    for rel in rels:
        oid = rel.target_id if rel.source_id == concept_id else rel.source_id
        o = db.get(Concept, oid)
        if o: related[rel.relation_type].append(ConceptResponse(id=o.id, name=o.name, description=o.description))
    return ConceptGraphResponse(concept=ConceptResponse(id=c.id, name=c.name, description=c.description), relations=dict(related))


# ── Ask ──

@app.post("/api/ask", response_model=AskResponse)
def ask(payload: AskRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    answer, chunks, parsed = answer_query(
        db=db, user_id=str(current_user.id), conversation_id=payload.conversation_id,
        prompt=payload.prompt, task=payload.task, understanding_level=payload.understanding_level,
        textbook_ids=payload.textbook_ids, group_name=payload.group_name,
        page_start=payload.page_start, page_end=payload.page_end,
    )
    sources = [SourceModel(textbook_id=c.get("textbook_id"), textbook=c["textbook_title"], chapter=c.get("chapter"), section=c.get("section"), page_start=c.get("page_start"), page_end=c.get("page_end"), group_name=c.get("group_name"), chunk_type=c.get("chunk_type"), rerank_score=c.get("rerank_score"), snippet=best_excerpt(c["content"], payload.prompt)) for c in chunks]
    return AskResponse(answer=answer, sources=sources, parsed=parsed)
