"""Database helpers for the SOEN 363 quizzer (SQLite).

The insert functions do NOT commit. Wrap them in `with conn:` so related
inserts are saved together (or rolled back together if something fails).
"""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id           INTEGER PRIMARY KEY,
    source_file  TEXT    NOT NULL,
    chunk_index  INTEGER NOT NULL,
    content_hash TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS questions (
    id          INTEGER PRIMARY KEY,
    chunk_id    INTEGER NOT NULL REFERENCES chunks(id),
    topic       TEXT    NOT NULL,
    qtype       TEXT    NOT NULL CHECK (qtype IN ('mcq', 'short')),
    prompt      TEXT    NOT NULL,
    choice_a    TEXT,
    choice_b    TEXT,
    choice_c    TEXT,
    choice_d    TEXT,
    answer      TEXT    NOT NULL,
    explanation TEXT,
    -- An MCQ must have all four choices and a letter answer.
    CHECK (
        qtype = 'short'
        OR (choice_a IS NOT NULL AND choice_b IS NOT NULL
            AND choice_c IS NOT NULL AND choice_d IS NOT NULL
            AND answer IN ('A', 'B', 'C', 'D'))
    )
);

CREATE TABLE IF NOT EXISTS attempts (
    id          INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    response    TEXT    NOT NULL,
    is_correct  INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    feedback    TEXT,
    answered_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection(path="quizzer.db"):
    """Open the database. Use ":memory:" as the path for tests."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["topic"]
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite ignores REFERENCES without this
    return conn


def init_db(conn):
    """Create the tables if they don't exist yet. Safe to run every time."""
    conn.executescript(SCHEMA)


def chunk_exists(conn, content_hash):
    """Return True if a chunk with this hash was already ingested."""
    row = conn.execute(
        "SELECT 1 FROM chunks WHERE content_hash = ?", (content_hash,)
    ).fetchone()
    return row is not None


def insert_chunk(conn, source_file, chunk_index, content_hash):
    """Insert a chunk and return its new id."""
    cur = conn.execute(
        "INSERT INTO chunks (source_file, chunk_index, content_hash) VALUES (?, ?, ?)",
        (source_file, chunk_index, content_hash),
    )
    return cur.lastrowid


def insert_question(conn, chunk_id, topic, qtype, prompt, answer,
                    choices=None, explanation=None):
    """Insert a question and return its new id.

    For an MCQ, `choices` is a list of 4 strings and `answer` is "A"-"D".
    For a short question, leave `choices` as None and put the model answer in `answer`.
    """
    if choices is None:
        choices = [None, None, None, None]
    a, b, c, d = choices
    cur = conn.execute(
        """INSERT INTO questions
               (chunk_id, topic, qtype, prompt,
                choice_a, choice_b, choice_c, choice_d, answer, explanation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (chunk_id, topic, qtype, prompt, a, b, c, d, answer, explanation),
    )
    return cur.lastrowid


def insert_attempt(conn, question_id, response, is_correct, feedback=None):
    """Record one answer. `is_correct` can be a bool; it's stored as 0 or 1."""
    cur = conn.execute(
        """INSERT INTO attempts (question_id, response, is_correct, feedback)
           VALUES (?, ?, ?, ?)""",
        (question_id, response, int(is_correct), feedback),
    )
    return cur.lastrowid


def get_topic_stats(conn):
    """Return one row per topic with: topic, attempts, correct.

    LEFT JOIN keeps topics that have questions but no attempts yet (attempts = 0).
    """
    return conn.execute(
        """SELECT q.topic,
                  COUNT(a.id)                  AS attempts,
                  COALESCE(SUM(a.is_correct), 0) AS correct
           FROM questions q
           LEFT JOIN attempts a ON a.question_id = q.id
           GROUP BY q.topic
           ORDER BY q.topic"""
    ).fetchall()


def get_questions_for_topic(conn, topic):
    """Return all questions for one topic."""
    return conn.execute(
        "SELECT * FROM questions WHERE topic = ? ORDER BY id", (topic,)
    ).fetchall()
