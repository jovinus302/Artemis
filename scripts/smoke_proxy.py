"""Online smoke test: runs root_agent through InMemoryRunner and prints the
function_call / function_response / final-text trace. No secrets are printed."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

from google.adk.runners import InMemoryRunner
from google.genai import types

from agents.artemis_agent.agent import root_agent

APP_NAME = "artemis_smoke"
USER_ID = "smoke_user"
SESSION_ID = "smoke_session"


async def main() -> None:
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID,
    )

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(
            text="Call the artemis_health tool and summarize the result in one line."
        )],
    )

    async for event in runner.run_async(
        user_id=USER_ID, session_id=SESSION_ID, new_message=message,
    ):
        print(f"--- event author={event.author} partial={event.partial} ---")
        if not event.content or not event.content.parts:
            continue
        for part in event.content.parts:
            if part.function_call:
                print(f"  function_call: {part.function_call.name}"
                      f"({dict(part.function_call.args or {})})")
            if part.function_response:
                print(f"  function_response: {part.function_response.name} ->"
                      f" {part.function_response.response}")
            if part.text:
                print(f"  text: {part.text}")


if __name__ == "__main__":
    asyncio.run(main())
