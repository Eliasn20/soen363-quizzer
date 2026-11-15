import sqlite3

import pytest

import db


@pytest.fixture
def conn():
    """A fresh, empty database (in memory) with the tables created."""
    conn = db.get_connection(":memory:")
    db.init_db(conn)
    return conn


def test_chunk_exists_and_insert(conn):
    # Initially, the chunk should not exist
    assert not db.chunk_exists(conn, "file1.txt", "hash1")

    # Insert a chunk; the first row in a new table gets id 1
    chunk_id = db.insert_chunk(conn, "file1.txt", 0, "hash1")
    assert chunk_id == 1

    # Now the chunk should exist
    assert db.chunk_exists(conn, "file1.txt", "hash1")


def test_same_hash_allowed_in_different_files(conn):
    db.insert_chunk(conn, "lec01.md", 0, "same-hash")

    # Same text in another file is a different chunk: not "already done"...
    assert not db.chunk_exists(conn, "lec02.md", "same-hash")
    # ...and it can be saved without breaking a UNIQUE rule.
    db.insert_chunk(conn, "lec02.md", 0, "same-hash")
    assert db.chunk_exists(conn, "lec02.md", "same-hash")


def test_same_hash_in_same_file_is_rejected(conn):
    db.insert_chunk(conn, "lec01.md", 0, "same-hash")
    with pytest.raises(sqlite3.IntegrityError):
        db.insert_chunk(conn, "lec01.md", 1, "same-hash")


def test_bad_mcq_is_rejected(conn):
    chunk_id = db.insert_chunk(conn, "file1.txt", 0, "hash1")

    # "E" is not a valid MCQ answer, so the CHECK constraint must reject it
    with pytest.raises(sqlite3.IntegrityError):
        db.insert_question(
            conn, chunk_id, "file1", "mcq", "What is 3NF?", "E",
            choices=["a", "b", "c", "d"],
        )


def test_topic_stats_counts_attempts_and_correct(conn):
    chunk_id = db.insert_chunk(conn, "lec01.md", 0, "hash1")
    q1 = db.insert_question(conn, chunk_id, "lec01", "short", "Define 3NF.", "...")
    db.insert_question(conn, chunk_id, "lec02", "short", "What is a B+ tree?", "...")
    db.insert_attempt(conn, q1, "my answer", True)
    db.insert_attempt(conn, q1, "my answer", False)

    stats = {row["topic"]: (row["attempts"], row["correct"]) for row in db.get_topic_stats(conn)}
    assert stats == {"lec01": (2, 1), "lec02": (0, 0)}  # lec02 kept by the LEFT JOIN


def test_get_questions_for_topic(conn):
    chunk_id = db.insert_chunk(conn, "lec01.md", 0, "hash1")
    db.insert_question(conn, chunk_id, "lec01", "short", "Q1", "...")
    db.insert_question(conn, chunk_id, "lec02", "short", "Q2", "...")

    rows = db.get_questions_for_topic(conn, "lec01")
    assert [row["prompt"] for row in rows] == ["Q1"]
