"""Offline sanity check: imports, versions, and which env vars are present."""
from importlib.metadata import version
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

for dist in ("google-adk", "anthropic", "artemis-client"):
    try:
        print(f"{dist:16s} {version(dist)}")
    except Exception as exc:                      # noqa: BLE001
        print(f"{dist:16s} MISSING ({exc})")

import google.adk                                  # noqa: E402,F401
from google.adk.models.anthropic_llm import AnthropicLlm   # noqa: E402,F401
from artemis_client import ArtemisClient           # noqa: E402,F401
print("imports OK")

for key in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
            "GEMINI_API_KEY", "ARTEMIS_BASE_URL"):
    print(f"{key:24s} {'SET' if os.environ.get(key) else '-'}")   # 값은 출력 금지

from agents.artemis_agent.model import build_model  # noqa: E402
print("model ->", type(build_model()).__name__)
