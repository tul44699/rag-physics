# Physics RAG

A RAG study assistant that lets you ask questions about your physics textbook, generate flashcards, and create study guides.

## Features

Upload a physics textbook PDF and then:
- Ask questions and get answers with inline LaTeX math
- Generate flashcards from chapter ranges
- Create study guides with key equations and practice problems
- Get chapter summaries
- Browse a formula sheet with every equation in the book

All answers include clickable citations.

## Setup

```bash
# PostgreSQL
docker compose up -d

# server 
cd server
cp ../.env.example .env
uv sync
uv run fastapi dev main.py

# client 
cd client
npm install
npm run dev
```

## Ingestion

```bash
cd server
uv run python scripts/ingest_textbook.py \
  --title "University Physics" \
  --pdf-path "/path/to/your/textbook.pdf" \
  --group-name "physics-core"
```

This sends the PDF to LlamaParse which converts it to markdown with LaTeX. Everything gets embedded into pgvector.

## Architecture

```
Client (React) ──REST──▶ Server (FastAPI) ──SQL──▶ PostgreSQL + pgvector
                              │
                              ├──▶ vLLM (chat + embeddings + rerank)
                              └──▶ LlamaParse (PDF extraction)
```

`main.py` handles routing, `services.py` runs the RAG pipeline (ingestion and answering), `retrieval.py` does hybrid search with RRF fusion, position-weighted dense search, section/chunk_type/page filtering, and three-tier reranking, `prompts.py` builds the system and user prompts, `config.py` manages settings and the LLM client, `embedding.py` handles remote and local embeddings, and `models.py` defines the database schema. Sources returned to the client include query-aware excerpts along with chunk type, section, and metadata.

## Tech Stack

| What | Using |
|---|---|
| Chat model | Qwen 3.5 instruct 9B via vLLM hosted on GCP |
| Embeddings | Qwen Embedding 0.6B (remote) or bge-large (local) |
| PDF parsing | LlamaParse cloud API |
| Vector DB | PostgreSQL with pgvector |
| Reranking | Chat model (remote) or cross-encoder (local) |
| Frontend | React, TypeScript, Vite, KaTeX |

## Config

Copy `.env.example` to `server/.env` and fill in:

| env var | use |
|---|---|
| `VLLM_BASE_URL` | Endpoint for hosted vLLM instance |
| `CHAT_MODEL` | Model name |
| `LLAMAPARSE_API_KEY` | LlamaParse API key (required for ingestion) |
| `EMBEDDING_BASE_URL` | Remote embeddings endpoint (optional, falls back to local) |
| `EMBEDDING_DIM` | Vector dimensions (1024, set based on your embedding model) |
| `NUM_SOURCES` | How many chunks to retrieve per query |
| `MIN_SOURCE_SCORE` | Relevance cutoff (0 = no filtering) |
| `JWT_SECRET` | Any random string for auth tokens |

## Testing

```bash
cd server && uv run pytest
```

Tests use a separate `physics_rag_test` database that gets created and destroyed automatically.
