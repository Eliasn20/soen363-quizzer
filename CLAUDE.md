# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

MVP done. Commands (inside the venv):
- Install: `pip install -r requirements.txt`
- Tests: `pytest`
- Run: `python quizzer.py ingest <notes folder>`, `python quizzer.py quiz -n 10`, `python quizzer.py stats`

Architecture:
- `chunker.py`: splits notes into ~3000-char chunks by paragraph; `chunk_hash` fingerprints them.
- `db.py`: SQLite schema (chunks, questions, attempts) and query functions. Insert functions don't commit; callers wrap them in `with conn:`.
- `generator.py`: OpenAI Responses API calls with structured outputs (generate 2 MCQ + 1 short per chunk; grade short answers).
- `quizzer.py`: argparse CLI. Topic = note filename. Quiz picks topics weighted by `(wrong+1)/(attempts+2)`; short-answer grading falls back to self-grading if the API fails.

## Environment

- This is a Python project. A local virtual environment lives at `.venv/` (gitignored). Activate it with `source .venv/bin/activate`.
- Secrets and configuration go in `.env` (gitignored). Never commit it.


## How to work with me
- I'm learning Python and the terminal. Write code when I ask for it.
- Keep code simple and readable. After making changes, explain each change in plain language.
- When I hit an error, explain what it means and why it happened before suggesting a fix.
- Before running any command, tell me what it does in one sentence.
- Never read, print, or commit the contents of .env.
- Keep changes small; one feature at a time.

## Project
- SOEN 363 quiz generator: reads lecture notes, calls the OpenAI Responses API to generate questions, stores them in SQLite, runs a CLI quiz.
- Python 3 in .venv (activate with: source .venv/bin/activate). Tests with pytest.