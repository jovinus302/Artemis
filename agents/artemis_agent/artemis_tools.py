"""ADK FunctionTools over the (dependency-free) artemis-client HTTP SDK."""
from __future__ import annotations

import os
from typing import Any


def _client():
    from artemis_client import ArtemisClient  # lazy import

    return ArtemisClient(
        os.environ.get("ARTEMIS_BASE_URL") or None,   # None이면 SDK가 DAEMON_HOST/PORT로 폴백
        token=os.environ.get("ARTEMIS_TOKEN") or None,
        device_serial=os.environ.get("ARTEMIS_DEVICE_SERIAL") or None,
        default_profile=os.environ.get("ARTEMIS_DEFAULT_PROFILE", "flash"),
        request_timeout=float(os.environ.get("ARTEMIS_REQUEST_TIMEOUT", "30")),
    )


def _err(exc: Exception) -> dict[str, Any]:
    return {
        "status": "error",
        "error_type": type(exc).__name__,
        "error": str(exc),
        "hint": "Start the ARTEMIS host (start.bat in the artemis repo root, or 'artemis ui' in the "
                "artemis repo) and set ARTEMIS_BASE_URL.",
    }


async def artemis_health() -> dict:
    """Checks whether the ARTEMIS Android-automation host is reachable.

    Returns a dict with 'status' ('success' or 'error') and the host's
    scheduler status when reachable.
    """
    try:
        client = _client()
        return {"status": "success", "base_url": client.base_url,
                "detail": dict(await client.health())}
    except Exception as exc:                      # noqa: BLE001
        return _err(exc)


async def artemis_list_devices() -> dict:
    """Lists the Android devices and emulators the ARTEMIS host can drive.

    Returns a dict with 'status' and, on success, 'devices': a list of
    {serial, state, model, busy}.
    """
    try:
        devices = await _client().list_devices()
        return {"status": "success", "devices": [
            {"serial": d.serial, "state": d.state, "model": d.model, "busy": d.busy}
            for d in devices]}
    except Exception as exc:                      # noqa: BLE001
        return _err(exc)


async def artemis_run_task(goal: str, profile: str = "flash",
                           device_serial: str = "") -> dict:
    """Runs one natural-language Android automation task and waits for the result.

    Args:
        goal: What to do on the phone, e.g. "Open Settings, go to Battery and
            report the current percentage".
        profile: "flash" for a fast reactive loop, "pro" for planning and
            verification on long multi-step workflows.
        device_serial: Optional target device serial, e.g. "emulator-5554".
            Leave empty to let ARTEMIS pick an available device.

    Returns a dict with 'status', 'succeeded', 'output', 'error', 'trace_id'.
    """
    try:
        result = await _client().run(
            goal,
            profile=profile if profile in ("flash", "pro") else None,
            device_serial=device_serial or None,
            timeout=float(os.environ.get("ARTEMIS_TASK_TIMEOUT", "1800")),
        )
        return {
            "status": "success" if result.succeeded else "failed",
            "succeeded": result.succeeded,
            "task_status": result.status,
            "output": result.output,
            "error": result.error,
            "turns": result.turns,
            "device_serial": result.device_serial,
            "trace_id": result.trace_id,
        }
    except Exception as exc:                      # noqa: BLE001
        return _err(exc)


async def artemis_get_task(task_id: str) -> dict:
    """Gets the current state of a previously submitted ARTEMIS task by its id."""
    try:
        r = await _client().get_task(task_id)
        return {"status": "success", "task_status": r.status, "done": r.done,
                "succeeded": r.succeeded, "output": r.output, "error": r.error}
    except Exception as exc:                      # noqa: BLE001
        return _err(exc)
