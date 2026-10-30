"""Explicit bank administration, separate from conversation retention."""

import asyncio
import math
from importlib.resources import files
from urllib.parse import quote

import httpx

from engineering_memory.settings import HindsightSettings


class ProvisionError(RuntimeError):
    """A safe operator-facing provisioning failure."""


def mission_text() -> str:
    """Return the packaged, canonical Architecture section 12 mission."""
    return files(__package__).joinpath("mission.txt").read_text(encoding="utf-8")


def provision(
    settings: HindsightSettings,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout: float = 60,
) -> None:
    """Apply only the retain mission and verify it; safe to rerun after interruption.

    PATCH config creates the missing bank in the pinned engine. No retention,
    deletion, or speculative retries occur. The optional transport is a test seam.
    """
    url = httpx.URL(str(settings.base_url))
    if url.username or url.password or url.query or url.fragment:
        raise ProvisionError("provisioning configuration invalid")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ProvisionError("provisioning deadline invalid")
    path = "/v1/default/banks/" + quote(settings.bank_id, safe="") + "/config"
    headers = {}
    if settings.token is not None:
        headers["Authorization"] = "Bearer " + settings.token.get_secret_value()
    mission = mission_text()

    async def run():
        async with asyncio.timeout(timeout):
            async with httpx.AsyncClient(
                trust_env=False,
                follow_redirects=False,
                transport=transport,
                headers=headers,
                timeout=min(30, timeout),
            ) as client:
                target = str(url).rstrip("/") + path
                for method in ("PATCH", "GET"):
                    kwargs = (
                        {"json": {"updates": {"retain_mission": mission}}}
                        if method == "PATCH"
                        else {}
                    )
                    response = await client.request(method, target, **kwargs)
                    if not response.is_success:
                        raise ProvisionError(
                            f"provisioning failed: engine HTTP {response.status_code}"
                        )
                try:
                    result = response.json()
                except ValueError:
                    raise ProvisionError("provisioning verification invalid") from None
                if (
                    not isinstance(result, dict)
                    or not isinstance(result.get("config"), dict)
                    or result["config"].get("retain_mission") != mission
                ):
                    raise ProvisionError("provisioning mission verification failed")

    try:
        asyncio.run(run())
    except (httpx.HTTPError, TimeoutError, UnicodeError):
        raise ProvisionError("provisioning unavailable") from None
