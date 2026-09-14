"""Offline smoke tests: no network, no API keys required."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.artemis_agent.agent import root_agent
from agents.artemis_agent.artemis_tools import artemis_health
from agents.artemis_agent.model import build_model


def test_root_agent_wiring():
    assert root_agent.name == "artemis_agent"
    assert len(root_agent.tools) >= 4


def test_build_model_anthropic_backend(monkeypatch):
    monkeypatch.setenv("ADK_MODEL_BACKEND", "anthropic")
    from google.adk.models.anthropic_llm import AnthropicLlm

    model = build_model()
    assert isinstance(model, AnthropicLlm)


def test_build_model_gemini_backend(monkeypatch):
    monkeypatch.setenv("ADK_MODEL_BACKEND", "gemini")
    model = build_model()
    assert isinstance(model, str)


def test_build_model_auto_prefers_anthropic_when_both_keys_present(monkeypatch):
    # Corporate network blocks direct Google API calls at the TLS handshake,
    # so auto mode must prefer the Anthropic-compatible proxy whenever an
    # ANTHROPIC_API_KEY is present, even if a GEMINI_API_KEY is also set.
    monkeypatch.setenv("ADK_MODEL_BACKEND", "auto")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    from google.adk.models.anthropic_llm import AnthropicLlm

    model = build_model()
    assert isinstance(model, AnthropicLlm)


def test_artemis_health_reports_error_without_host(monkeypatch):
    # Port 1 is a closed/unreachable port, so the client fails fast.
    monkeypatch.setenv("ARTEMIS_BASE_URL", "http://127.0.0.1:1")
    result = asyncio.run(artemis_health())
    assert result["status"] == "error"
