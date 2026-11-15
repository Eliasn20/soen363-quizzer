"""Tests for quizzer.ingest. The OpenAI call is replaced with a fake, so no API is used."""

import pytest

import db
import generator
import quizzer

ONE_QUESTION = [{
    "qtype": "short",
    "prompt": "Define 3NF.",
    "choices": [],
    "answer": "No transitive dependencies on the key.",
    "explanation": "That is the definition.",
}]


@pytest.fixture
def conn():
    conn = db.get_connection(":memory:")
    db.init_db(conn)
    return conn


def count_chunks(conn):
    return conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]


def test_chunk_with_no_questions_is_not_saved(conn, tmp_path, monkeypatch):
    (tmp_path / "lec01.md").write_text("Some notes about normalization.")
    monkeypatch.setattr(generator, "generate_questions", lambda chunk: [])

    quizzer.ingest(conn, tmp_path)

    # Not saved, so the next ingest will try this chunk again.
    assert count_chunks(conn) == 0


def test_same_text_in_two_files_is_ingested_for_both(conn, tmp_path, monkeypatch):
    (tmp_path / "lec01.md").write_text("Shared paragraph.")
    (tmp_path / "lec02.md").write_text("Shared paragraph.")
    monkeypatch.setattr(generator, "generate_questions", lambda chunk: ONE_QUESTION)

    quizzer.ingest(conn, tmp_path)

    topics = [row["topic"] for row in db.get_topic_stats(conn)]
    assert topics == ["lec01", "lec02"]


def test_fatal_api_error_stops_the_whole_run(conn, tmp_path, monkeypatch):
    (tmp_path / "lec01.md").write_text("First.")
    (tmp_path / "lec02.md").write_text("Second.")
    calls = []

    def fake_generate(chunk):
        calls.append(chunk)
        raise generator.FatalAPIError("OpenAI rejected the API key.")

    monkeypatch.setattr(generator, "generate_questions", fake_generate)

    with pytest.raises(SystemExit) as exc:
        quizzer.ingest(conn, tmp_path)

    assert len(calls) == 1  # stopped after the first chunk, didn't try the second
    assert "OpenAI rejected the API key." in str(exc.value)


def test_other_errors_skip_only_that_chunk(conn, tmp_path, monkeypatch):
    (tmp_path / "lec01.md").write_text("First.")
    (tmp_path / "lec02.md").write_text("Second.")

    def fake_generate(chunk):
        if chunk == "First.":
            raise RuntimeError("temporary network problem")
        return ONE_QUESTION

    monkeypatch.setattr(generator, "generate_questions", fake_generate)

    quizzer.ingest(conn, tmp_path)

    topics = [row["topic"] for row in db.get_topic_stats(conn)]
    assert topics == ["lec02"]
