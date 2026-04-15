from argparse import ArgumentParser

from db import SessionLocal
from services import ingest_textbook


def main() -> None:
    parser = ArgumentParser(description="Ingest a textbook PDF into pgvector")
    parser.add_argument("--title", required=True)
    parser.add_argument("--pdf-path", required=True)
    parser.add_argument("--group-name", default=None)
    parser.add_argument("--chapter-hint", default=None)
    parser.add_argument("--chunk-size", type=int, default=900)
    parser.add_argument("--chunk-overlap", type=int, default=220)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        textbook_id, chunk_count = ingest_textbook(
            db=db,
            title=args.title,
            pdf_path=args.pdf_path,
            group_name=args.group_name,
            chapter_hint=args.chapter_hint,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        print(f"Ingested textbook_id={textbook_id}, chunks={chunk_count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
