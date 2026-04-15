"""Migrate pgvector columns from 768-dim to 1024-dim (for bge-large).

This drops existing vector data since dimensions must match.
Re-ingestion is required after running this script.
"""

from sqlalchemy import text

from db import engine


def migrate() -> None:
    with engine.connect() as conn:
        # Drop and recreate vector columns with new dimension
        for table in ["text_chunks", "equations", "concepts"]:
            conn.execute(text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS embedding"))
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN embedding vector(1024)"))
            conn.commit()
            print(f"Migrated {table}.embedding → vector(1024)")

    print("\nDone. Re-ingest all textbooks to populate embeddings.")


if __name__ == "__main__":
    confirm = input("This will DROP all existing embeddings. Continue? [y/N] ")
    if confirm.lower() == "y":
        migrate()
    else:
        print("Aborted.")
