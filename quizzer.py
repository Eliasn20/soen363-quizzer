"""SOEN 363 quizzer: command-line entry point.

Usage:
    python quizzer.py ingest notes/
    python quizzer.py quiz -n 10
    python quizzer.py stats
"""

import argparse
import random
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # loads .env (OPENAI_API_KEY, OPENAI_MODEL); generator reads them at request time

import db  # noqa: E402
import generator  # noqa: E402
from chunker import chunk_hash, split_into_chunks  # noqa: E402

DB_PATH = "quizzer.db"
LETTERS = ["A", "B", "C", "D"]


# ---------- ingest ----------

def find_note_files(path):
    """Return the .md/.txt files at `path` (a single file or a folder)."""
    path = Path(path)
    if path.is_file():
        return [path]
    return sorted(list(path.glob("*.md")) + list(path.glob("*.txt")))


def shuffle_choices(choices, answer, rng=random):
    """Return (shuffled choices, new answer letter) so the answer isn't always in the same spot.

    `answer` is "A"-"D". The original `choices` list is not changed.
    """
    correct = choices[LETTERS.index(answer)]
    shuffled = list(choices)  # copy, so the caller's list stays as it was
    rng.shuffle(shuffled)
    return shuffled, LETTERS[shuffled.index(correct)]


def ingest(conn, path):
    files = find_note_files(path)
    if not files:
        print(f"No .md or .txt files found at {path}")
        return

    for file in files:
        topic = file.stem  # "lecture03-normalization.md" -> "lecture03-normalization"
        chunks = split_into_chunks(file.read_text(encoding="utf-8"))
        print(f"{file.name}: {len(chunks)} chunk(s)")

        for index, chunk in enumerate(chunks):
            h = chunk_hash(chunk)
            if db.chunk_exists(conn, str(file), h):
                print(f"  chunk {index}: already done, skipping")
                continue

            try:
                questions = generator.generate_questions(chunk)
            except generator.FatalAPIError as e:
                # Every other chunk would fail the same way, so stop now.
                raise SystemExit(f"Stopping ingest: {e}")
            except Exception as e:
                # Nothing saved, so this chunk will be retried next time.
                print(f"  chunk {index}: API error, skipping ({e})")
                continue

            if not questions:
                # Nothing saved, so this chunk will be retried next time.
                print(f"  chunk {index}: no valid questions, skipping")
                continue

            with conn:  # chunk + its questions are saved together, or not at all
                chunk_id = db.insert_chunk(conn, str(file), index, h)
                for q in questions:
                    choices, answer = None, q["answer"]
                    if q["qtype"] == "mcq":
                        choices, answer = shuffle_choices(q["choices"], q["answer"])
                    db.insert_question(
                        conn, chunk_id, topic, q["qtype"], q["prompt"], answer,
                        choices=choices,
                        explanation=q["explanation"],
                    )
            print(f"  chunk {index}: saved {len(questions)} question(s)")


# ---------- quiz ----------

def topic_weight(attempts, correct):
    """New topic -> 0.5, always right -> toward 0, always wrong -> toward 1."""
    wrong = attempts - correct
    return (wrong + 1) / (attempts + 2)


def ask_mcq(question):
    """Show an MCQ, read a letter, return (response, is_correct, feedback)."""
    choices = [question["choice_a"], question["choice_b"],
               question["choice_c"], question["choice_d"]]
    for letter, choice in zip(LETTERS, choices):
        print(f"  {letter}) {choice}")

    response = ""
    while response not in LETTERS:
        response = input("Your answer (A-D): ").strip().upper()

    is_correct = response == question["answer"]
    return response, is_correct, None


def ask_short(question):
    """Show a short question, grade it with the API, return (response, is_correct, feedback)."""
    response = input("Your answer: ").strip()
    try:
        is_correct, feedback = generator.grade_short_answer(
            question["prompt"], question["answer"], response
        )
    except Exception as e:
        # Fallback: if the API fails, let the student grade themselves.
        print(f"(AI grading failed: {e})")
        print(f"Model answer: {question['answer']}")
        is_correct = input("Did you get it? [y/n]: ").strip().lower().startswith("y")
        feedback = None
    return response, is_correct, feedback


def quiz(conn, n):
    stats = db.get_topic_stats(conn)
    if not stats:
        print("No questions yet. Run: python quizzer.py ingest <notes folder>")
        return

    # Weights are computed once, at the start of the session.
    weights = {row["topic"]: topic_weight(row["attempts"], row["correct"]) for row in stats}
    asked = set()
    score = 0

    for number in range(1, n + 1):
        # Pick a topic (weighted), then a random question from it not asked yet.
        question = None
        while weights and question is None:
            topic = random.choices(list(weights), weights=list(weights.values()))[0]
            remaining = [q for q in db.get_questions_for_topic(conn, topic) if q["id"] not in asked]
            if remaining:
                question = random.choice(remaining)
            else:
                del weights[topic]  # this topic is used up for this session
        if question is None:
            print("No more new questions this session.")
            break
        asked.add(question["id"])

        print(f"\nQ{number} [{question['topic']}] {question['prompt']}")
        if question["qtype"] == "mcq":
            response, is_correct, feedback = ask_mcq(question)
        else:
            response, is_correct, feedback = ask_short(question)

        with conn:
            db.insert_attempt(conn, question["id"], response, is_correct, feedback)

        if is_correct:
            score += 1
            print("Correct!")
        else:
            print(f"Wrong. Answer: {question['answer']}")
        if feedback:
            print(f"Feedback: {feedback}")
        if question["explanation"]:
            print(f"Why: {question['explanation']}")

    print(f"\nScore: {score}/{len(asked)}")


# ---------- stats ----------

def show_stats(conn):
    rows = db.get_topic_stats(conn)
    if not rows:
        print("No questions yet.")
        return

    def accuracy(row):
        return row["correct"] / row["attempts"] if row["attempts"] else None

    # Worst topics first; topics never attempted go last.
    rows = sorted(rows, key=lambda r: (accuracy(r) is None, accuracy(r) or 0))

    print(f"{'Topic':<35} {'Attempts':>8} {'Correct':>8} {'Accuracy':>9}")
    for row in rows:
        acc = accuracy(row)
        acc_text = f"{acc:.0%}" if acc is not None else "-"
        print(f"{row['topic']:<35} {row['attempts']:>8} {row['correct']:>8} {acc_text:>9}")


# ---------- command line ----------

def main():
    parser = argparse.ArgumentParser(description="SOEN 363 quiz generator")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="generate questions from notes")
    p_ingest.add_argument("path", help="a .md/.txt file or a folder of them")

    p_quiz = sub.add_parser("quiz", help="take a quiz")
    p_quiz.add_argument("-n", type=int, default=10, help="number of questions (default 10)")

    sub.add_parser("stats", help="show accuracy per topic")

    args = parser.parse_args()

    conn = db.get_connection(DB_PATH)
    db.init_db(conn)
    try:
        if args.command == "ingest":
            ingest(conn, args.path)
        elif args.command == "quiz":
            quiz(conn, args.n)
        elif args.command == "stats":
            show_stats(conn)
    except KeyboardInterrupt:
        print("\nBye!")  # Ctrl+C exits cleanly; answers so far are already saved
    finally:
        conn.close()


if __name__ == "__main__":
    main()
