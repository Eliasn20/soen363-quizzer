"""All calls to the OpenAI Responses API live here."""

import json
import os

from openai import OpenAI

# Change the model with OPENAI_MODEL in .env. Check OpenAI's models page for current names.
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

# The shape we force the model to answer in (structured outputs).
# Strict mode requires every property to be "required" and no extra properties.
QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "qtype": {"type": "string", "enum": ["mcq", "short"]},
                    "prompt": {"type": "string"},
                    "choices": {"type": "array", "items": {"type": "string"}},
                    "answer": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["qtype", "prompt", "choices", "answer", "explanation"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["questions"],
    "additionalProperties": False,
}

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "is_correct": {"type": "boolean"},
        "feedback": {"type": "string"},
    },
    "required": ["is_correct", "feedback"],
    "additionalProperties": False,
}

GENERATE_INSTRUCTIONS = """You write quiz questions for SOEN 363, a university databases course.
Using ONLY the lecture notes you are given, write exactly 3 questions:
- 2 with qtype "mcq": exactly 4 choices (plain text, no "A)" prefixes),
  and "answer" is the letter of the correct choice: "A", "B", "C" or "D".
- 1 with qtype "short": "choices" is an empty list, and "answer" is a
  concise model answer (1-3 sentences).
"explanation" is 1-2 sentences on why the answer is correct."""

GRADE_INSTRUCTIONS = """You grade a student's short answer for a university databases course.
Compare the student's answer with the model answer. Mark it correct if it
captures the key idea, even if worded differently. Give 1-2 sentences of feedback."""

_client = None


def _get_client():
    """Create the OpenAI client once. It reads OPENAI_API_KEY from the environment."""
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def _ask(instructions, user_input, schema_name, schema):
    """Send one request and return the parsed JSON answer as a dict."""
    response = _get_client().responses.create(
        model=MODEL,
        instructions=instructions,
        input=user_input,
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema,
                "strict": True,
            }
        },
    )
    return json.loads(response.output_text)


def _is_valid(question):
    """Structured outputs guarantee the shape, but not these rules, so check them."""
    if question["qtype"] == "mcq":
        return len(question["choices"]) == 4 and question["answer"] in ("A", "B", "C", "D")
    return True


def generate_questions(chunk):
    """Return a list of question dicts generated from one chunk of notes."""
    data = _ask(GENERATE_INSTRUCTIONS, f"Lecture notes:\n\n{chunk}",
                "quiz_questions", QUESTIONS_SCHEMA)
    return [q for q in data["questions"] if _is_valid(q)]


def grade_short_answer(prompt, model_answer, student_answer):
    """Return (is_correct, feedback) for a short-answer question."""
    user_input = (
        f"Question: {prompt}\n\n"
        f"Model answer: {model_answer}\n\n"
        f"Student answer: {student_answer}"
    )
    data = _ask(GRADE_INSTRUCTIONS, user_input, "grade", GRADE_SCHEMA)
    return data["is_correct"], data["feedback"]
