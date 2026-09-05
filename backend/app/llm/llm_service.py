from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


# ============================================================
# LLM SERVICE
# ============================================================


class LLMService:
    """
    Central Groq LLM service for ZenUI.

    Responsibilities:

        - Load LLM configuration
        - Generate normal text
        - Generate structured JSON
        - Keep all Groq access in one place

    The rest of ZenUI should NOT create Groq clients directly.
    """

    def __init__(self) -> None:

        api_key = (
            os.getenv("GROQ_API_KEY")
            or ""
        ).strip()

        model = (
            os.getenv("GROQ_MODEL")
            or ""
        ).strip()

        if not api_key:

            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        if not model:

            raise RuntimeError(
                "GROQ_MODEL is not configured."
            )

        self.model = model

        self.client = Groq(
            api_key=api_key,
        )

    # ========================================================
    # TEXT GENERATION
    # ========================================================

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> str:

        if not prompt:

            raise ValueError(
                "LLM prompt cannot be empty."
            )

        return await asyncio.to_thread(
            self._generate_sync,
            prompt,
            temperature,
            max_tokens,
        )

    # ========================================================
    # SYNC TEXT GENERATION
    # ========================================================

    def _generate_sync(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:

        response = (
            self.client
            .chat
            .completions
            .create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
            )
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        return (
            content or ""
        ).strip()

    # ========================================================
    # JSON GENERATION
    # ========================================================

    async def generate_json(
        self,
        prompt: str,
        *,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:

        if not prompt:

            raise ValueError(
                "LLM JSON prompt cannot be empty."
            )

        raw = await asyncio.to_thread(
            self._generate_json_sync,
            prompt,
            max_tokens,
        )

        return self._parse_json(
            raw
        )

    # ========================================================
    # SYNC JSON GENERATION
    # ========================================================

    def _generate_json_sync(
        self,
        prompt: str,
        max_tokens: int,
    ) -> str:

        response = (
            self.client
            .chat
            .completions
            .create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0,
                max_completion_tokens=max_tokens,
                response_format={
                    "type": "json_object"
                },
            )
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        return (
            content or "{}"
        ).strip()

    # ========================================================
    # JSON PARSER
    # ========================================================

    @staticmethod
    def _parse_json(
        raw: str,
    ) -> dict[str, Any]:

        text = (
            raw or ""
        ).strip()

        if not text:

            return {}

        # ----------------------------------------------------
        # Remove markdown code fences
        # ----------------------------------------------------

        if text.startswith(
            "```"
        ):

            text = re.sub(
                r"^```(?:json)?\s*",
                "",
                text,
                flags=re.IGNORECASE,
            )

            text = re.sub(
                r"\s*```$",
                "",
                text,
            )

        # ----------------------------------------------------
        # Direct JSON
        # ----------------------------------------------------

        try:

            value = json.loads(
                text
            )

            if isinstance(
                value,
                dict,
            ):

                return value

        except json.JSONDecodeError:

            pass

        # ----------------------------------------------------
        # Extract JSON object
        # ----------------------------------------------------

        match = re.search(
            r"\{.*\}",
            text,
            flags=re.DOTALL,
        )

        if match:

            try:

                value = json.loads(
                    match.group(0)
                )

                if isinstance(
                    value,
                    dict,
                ):

                    return value

            except json.JSONDecodeError:

                pass

        raise ValueError(
            "LLM returned invalid JSON."
        )