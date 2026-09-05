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


LINKUP_TOOL = ToolDefinition(
    name="linkup",
    description=(
        "Perform source-backed web research for "
        "research-oriented and detailed information."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The research query."
                ),
            },
            "depth": {
                "type": "string",
                "description": (
                    "Research depth."
                ),
                "enum": [
                    "standard",
                    "deep",
                ],
                "default": "standard",
            },
        },
        "required": [
            "query",
        ],
    },
)


# ============================================================
# LINKUP TOOL
# ============================================================


class LinkupTool:

    BASE_URL = (
        "https://api.linkup.so/v1/search"
    )

    async def execute(
        self,
        query: str,
        depth: str = "standard",
    ) -> dict[str, Any]:

        api_key = (
            settings.linkup_api_key
        )

        if not api_key:

            raise RuntimeError(
                "LINKUP_API_KEY is not configured."
            )

        query = (
            query or ""
        ).strip()

        if not query:

            raise ValueError(
                "Linkup query cannot be empty."
            )

        depth = (
            depth or "standard"
        ).strip().lower()

        if depth not in {
            "standard",
            "deep",
        }:

            depth = "standard"

        payload = {
            "q": query,
            "depth": depth,
            "outputType": "searchResults",
        }

        headers = {
            "Authorization": (
                f"Bearer {api_key}"
            ),
            "Content-Type": "application/json",
        }

        try:

            async with httpx.AsyncClient(
                timeout=30.0
            ) as client:

                response = await client.post(
                    self.BASE_URL,
                    json=payload,
                    headers=headers,
                )

                if response.status_code >= 400:

                    print()
                    print(
                        "========== LINKUP ERROR =========="
                    )

                    print(
                        "STATUS:",
                        response.status_code,
                    )

                    print(
                        "PAYLOAD:",
                        payload,
                    )

                    print(
                        "BODY:",
                        response.text,
                    )

                    print(
                        "=================================="
                    )

                response.raise_for_status()

                raw = response.json()

        except httpx.HTTPStatusError as error:

            raise RuntimeError(
                "Linkup API returned HTTP "
                f"{error.response.status_code}: "
                f"{error.response.text}"
            ) from error

        except httpx.RequestError as error:

            raise RuntimeError(
                f"Linkup request failed: {error}"
            ) from error

        return {
            "source": "linkup",
            "query": query,
            "depth": depth,
            "results": raw,
        }