from google.adk.agents import LlmAgent

from .artemis_tools import (artemis_get_task, artemis_health,
                            artemis_list_devices, artemis_run_task)
from .mcp_tools import build_artemis_mcp_toolset
from .model import build_model

_INSTRUCTION = """You drive real Android devices through the ARTEMIS host.

Rules:
1. Before the first automation task in a conversation, call `artemis_health`.
   If it returns status "error", tell the user the ARTEMIS host is not running
   and stop - do not invent device results.
2. Use `artemis_list_devices` when the user mentions a specific phone or when
   more than one device may be connected.
3. Use profile "flash" for short deterministic UI flows and "pro" for long
   multi-step workflows that need a plan and verification.
4. Report what actually happened, quoting `output` and `trace_id` from the
   tool result. Never claim a UI state you did not observe.
"""

_tools = [artemis_health, artemis_list_devices, artemis_run_task, artemis_get_task]
_mcp = build_artemis_mcp_toolset()
if _mcp is not None:
    _tools.append(_mcp)

root_agent = LlmAgent(
    model=build_model(),
    name="artemis_agent",
    description="Runs natural-language Android automation tasks via Google ARTEMIS.",
    instruction=_INSTRUCTION,
    tools=_tools,
)
