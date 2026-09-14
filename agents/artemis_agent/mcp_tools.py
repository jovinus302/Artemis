"""Optional bridge to the ARTEMIS native MCP server (5 mobile_* tools).

Requires:  pip install -r requirements-mcp.txt
           a local clone of github.com/google/artemis whose .venv has the full
           ARTEMIS runtime installed (run start.bat once in that clone).
"""
from __future__ import annotations

import os
from pathlib import Path


def build_artemis_mcp_toolset():
    if (os.environ.get("ARTEMIS_MCP_ENABLED", "false").strip().lower()
            not in ("1", "true", "yes")):
        return None
    repo = os.environ.get("ARTEMIS_REPO_DIR")
    if not repo:
        return None

    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
    from mcp import StdioServerParameters

    repo_path = Path(repo).resolve()
    python_exe = repo_path / ".venv" / "Scripts" / "python.exe"   # Windows

    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=str(python_exe),
                args=["-m", "mcp_server"],
                cwd=str(repo_path),
                env={
                    "PYTHONUNBUFFERED": "1",
                    "PYTHONPATH": str(repo_path),
                    **({"GEMINI_API_KEY": os.environ["GEMINI_API_KEY"]}
                       if os.environ.get("GEMINI_API_KEY") else {}),
                },
            ),
            timeout=120.0,
        ),
        tool_filter=[
            "mobile_run_task", "mobile_manage_task", "mobile_get_device_state",
            "mobile_inspect_trace", "mobile_diagnose",
        ],
    )
