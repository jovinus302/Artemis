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


def test_artemis_health_reports_error_without_host(monkeypatch):
    # Port 1 is a closed/unreachable port, so the client fails fast.
    monkeypatch.setenv("ARTEMIS_BASE_URL", "http://127.0.0.1:1")
    result = asyncio.run(artemis_health())
    assert result["status"] == "error"
