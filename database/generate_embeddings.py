#!/usr/bin/env python3
"""
FinServ Agents — Generate pgvector embeddings for recovery narratives.

Uses OpenAI text-embedding-3-small to embed each recovery_history.narrative,
then updates the embedding column in PostgreSQL via pgvector.
"""

import os
import time

import psycopg2
from openai import OpenAI

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/loanops",
)

client = OpenAI()
MODEL = "text-embedding-3-small"
BATCH_SIZE = 50  # OpenAI supports up to 2048 inputs per call


def get_narratives(conn):
    """Fetch all narratives that don't have embeddings yet."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, narrative FROM recovery_history WHERE embedding IS NULL"
        )
        return cur.fetchall()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using OpenAI."""
    response = client.embeddings.create(model=MODEL, input=texts)
    return [item.embedding for item in response.data]


def update_embeddings(conn, updates: list[tuple]):
    """Update embedding column for each record."""
    with conn.cursor() as cur:
        for record_id, embedding in updates:
            # Convert to pgvector format: [0.1, 0.2, ...]
            vec_str = "[" + ",".join(str(x) for x in embedding) + "]"
            cur.execute(
                "UPDATE recovery_history SET embedding = %s WHERE id = %s",
                (vec_str, record_id),
            )
    conn.commit()


def main():
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(DB_URL)

    narratives = get_narratives(conn)
    total = len(narratives)
    print(f"Found {total} narratives without embeddings.\n")

    if total == 0:
        print("Nothing to do — all narratives already have embeddings.")
        conn.close()
        return

    processed = 0
    for i in range(0, total, BATCH_SIZE):
        batch = narratives[i : i + BATCH_SIZE]
        ids = [row[0] for row in batch]
        texts = [row[1] for row in batch]

        print(f"  Embedding batch {i // BATCH_SIZE + 1} ({len(batch)} items)...")

        try:
            embeddings = embed_batch(texts)
        except Exception as e:
            print(f"  Error embedding batch: {e}")
            print("  Waiting 30s before retry...")
            time.sleep(30)
            embeddings = embed_batch(texts)

        updates = list(zip(ids, embeddings))
        update_embeddings(conn, updates)
        processed += len(batch)
        print(f"  Updated {processed}/{total}")

        # Rate limit buffer
        if i + BATCH_SIZE < total:
            time.sleep(0.5)

    conn.close()
    print(f"\nDone! Embedded {processed} narratives.")


if __name__ == "__main__":
    main()
