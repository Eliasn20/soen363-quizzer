"""Tests for generator.py. A fake client stands in for OpenAI, so no API is used."""

import json
from types import SimpleNamespace

import httpx2
import openai
import pytest

import generator

REQUEST = httpx2.Request("POST", "https://api.openai.com/v1/responses")


def fake_client(create):
    """Build an object shaped like OpenAI() where responses.create is `create`."""
    return SimpleNamespace(responses=SimpleNamespace(create=create))


def ok_response(**kwargs):
    return SimpleNamespace(output_text=json.dumps({"questions": []}))


def api_error(cls, status, body):
    return cls("error from OpenAI", response=httpx2.Response(status, request=REQUEST), body=body)


@pytest.fixture(autouse=True)
def no_cached_client(monkeypatch):
    """Each test starts without a cached client and without OPENAI_MODEL set."""
    monkeypatch.setattr(generator, "_client", None)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)


def test_default_model_is_gpt_6_luna(monkeypatch):
    seen = {}

    def create(**kwargs):
        seen.update(kwargs)
        return ok_response()

    monkeypatch.setattr(generator, "_client", fake_client(create))
    generator.generate_questions("notes")
    assert seen["model"] == "gpt-6-luna"


def test_openai_model_env_var_overrides_default(monkeypatch):
    seen = {}

    def create(**kwargs):
        seen.update(kwargs)
        return ok_response()

    monkeypatch.setenv("OPENAI_MODEL", "my-custom-model")
    monkeypatch.setattr(generator, "_client", fake_client(create))
    generator.generate_questions("notes")
    assert seen["model"] == "my-custom-model"


def test_missing_api_key_is_fatal(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(generator.FatalAPIError, match="OPENAI_API_KEY"):
        generator.generate_questions("notes")


def test_invalid_api_key_is_fatal(monkeypatch):
    def create(**kwargs):
        raise api_error(openai.AuthenticationError, 401, {"code": "invalid_api_key"})

    monkeypatch.setattr(generator, "_client", fake_client(create))
    with pytest.raises(generator.FatalAPIError, match="OPENAI_API_KEY"):
        generator.generate_questions("notes")


def test_rejected_model_name_is_fatal_and_names_the_model(monkeypatch):
    def create(**kwargs):
        raise api_error(openai.NotFoundError, 404, {"code": "model_not_found", "param": "model"})

    monkeypatch.setenv("OPENAI_MODEL", "no-such-model")
    monkeypatch.setattr(generator, "_client", fake_client(create))
    with pytest.raises(generator.FatalAPIError, match="no-such-model"):
        generator.generate_questions("notes")


def test_other_api_errors_are_not_fatal(monkeypatch):
    def create(**kwargs):
        raise api_error(openai.BadRequestError, 400, {"code": "invalid_value", "param": "input"})

    monkeypatch.setattr(generator, "_client", fake_client(create))
    with pytest.raises(openai.BadRequestError):
        generator.generate_questions("notes")
