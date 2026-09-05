from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings

from app.tools.tool_models import (
    ToolDefinition,
)


# ============================================================
# TOOL DEFINITION
# ============================================================


SERPER_TOOL = ToolDefinition(
    name="serper",
    description=(
        "Search the public web for current information "
        "that is not available through ZenUI internal "
        "resources."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The public web search query."
                ),
            },
            "num_results": {
                "type": "integer",
                "description": (
                    "Maximum number of results."
                ),
                "default": 5,
            },
        },
        "required": [
            "query",
        ],
    },
)


# ============================================================
# SERPER TOOL
# ============================================================


class SerperTool:

    BASE_URL = (
        "https://google.serper.dev/search"
    )

    async def execute(
        self,
        query: str,
        num_results: int = 5,
    ) -> dict[str, Any]:

        api_key = (
            settings.serper_api_key
        )

        if not api_key:

            raise RuntimeError(
                "SERPER_API_KEY is not configured."
            )

        query = (
            query or ""
        ).strip()

        if not query:

            raise ValueError(
                "Search query cannot be empty."
            )

        num_results = max(
            1,
            min(
                int(num_results),
                10,
            ),
        )

        payload = {
            "q": query,
            "num": num_results,
        }

        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        }

        try:

            async with httpx.AsyncClient(
                timeout=20.0
            ) as client:

                response = await client.post(
                    self.BASE_URL,
                    json=payload,
                    headers=headers,
                )

                response.raise_for_status()

                raw = response.json()

        except httpx.HTTPStatusError as error:

            raise RuntimeError(
                "Serper API returned HTTP "
                f"{error.response.status_code}: "
                f"{error.response.text}"
            ) from error

        except httpx.RequestError as error:

            raise RuntimeError(
                f"Serper request failed: {error}"
            ) from error

        return {
            "source": "serper",
            "query": query,
            "num_results": num_results,
            "results": raw,
        }