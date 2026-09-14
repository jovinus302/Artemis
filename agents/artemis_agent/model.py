"""LLM backend selection: Anthropic-compatible proxy (default) or Gemini."""
from __future__ import annotations

import os

from google.adk.models.base_llm import BaseLlm


def _backend() -> str:
    choice = (os.environ.get("ADK_MODEL_BACKEND") or "auto").strip().lower()
    if choice in ("anthropic", "gemini"):
        return choice
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return "anthropic"


def build_model() -> BaseLlm | str:
    if _backend() == "gemini":
        # 문자열은 ADK LLM 레지스트리가 Gemini 클래스로 해석한다.
        return os.environ.get("ADK_GEMINI_MODEL", "gemini-flash-latest")

    from google.adk.models.anthropic_llm import AnthropicLlm

    # !!! 반드시 인스턴스로 넘긴다.
    # ADK 레지스트리는 r'claude-.*' 패턴을 anthropic_llm.Claude 로 매핑하는데,
    # Claude 는 AsyncAnthropicVertex 를 쓰는 *Vertex AI* 전용 서브클래스라
    # GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION 이 없으면 ValueError 로 죽는다.
    # AnthropicLlm(부모)은 인자 없는 AsyncAnthropic() 을 만들고, 공식 Anthropic SDK가
    # ANTHROPIC_BASE_URL / ANTHROPIC_API_KEY 를 환경변수에서 스스로 읽는다.
    return AnthropicLlm(
        model=os.environ.get("ADK_ANTHROPIC_MODEL", "claude-sonnet-5"),
        max_tokens=int(os.environ.get("ADK_MAX_TOKENS", "8192")),
    )
