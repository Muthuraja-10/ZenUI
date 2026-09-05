from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.llm.llm_service import LLMService


# ============================================================
# UI COMPONENT
# ============================================================


class UIComponent(BaseModel):

    id: str

    type: str

    label: Optional[str] = None

    properties: dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================
# UI STATE
# ============================================================


class UIState(BaseModel):

    components: list[UIComponent] = Field(
        default_factory=list
    )


# ============================================================
# RESULT
# ============================================================


class ContextResult(BaseModel):

    operation: str = "create"

    target_component: Optional[str] = None

    has_existing_ui: bool = False

    context_used: bool = False

    context_summary: Optional[str] = None

    relevant_components: list[str] = Field(
        default_factory=list
    )


# ============================================================
# ANALYZER
# ============================================================


class ContextAnalyzer:

    def __init__(self):

        self.llm = LLMService()

    # ========================================================
    # PUBLIC
    # ========================================================

    async def analyze(
        self,
        user_prompt: str,
        ui_state: Optional[Any] = None,
        conversation_history: Optional[list[dict]] = None,
    ) -> ContextResult:

        normalized_state = (
            self._normalize_ui_state(
                ui_state
            )
        )

        has_existing_ui = (
            normalized_state is not None
            and len(
                normalized_state.components
            ) > 0
        )

        existing_ui = (
            self._serialize_ui_state(
                normalized_state
            )
        )

        history = (
            self._serialize_history(
                conversation_history
            )
        )

        prompt = self._build_prompt(
            user_prompt=user_prompt,
            existing_ui=existing_ui,
            conversation_history=history,
        )

        try:

            raw_response = (
                await self.llm.generate(
                    prompt
                )
            )

            data = self._parse_json(
                raw_response
            )

        except Exception as error:

            print(
                "\n========== CONTEXT ERROR =========="
            )

            print(error)

            # Fail safe: a context-analysis failure must never
            # silently convert a fresh request into a UI
            # modification that reuses stale data.
            return ContextResult(
                operation="create",
                has_existing_ui=has_existing_ui,
                context_used=False,
            )

        return ContextResult(
            operation=data.get(
                "operation",
                "create",
            ),
            target_component=data.get(
                "target_component"
            ),
            has_existing_ui=has_existing_ui,
            context_used=data.get(
                "context_used",
                False,
            ),
            context_summary=data.get(
                "context_summary"
            ),
            relevant_components=data.get(
                "relevant_components",
                [],
            ),
        )

    # ========================================================
    # PROMPT
    # ========================================================

    @staticmethod
    def _build_prompt(
        user_prompt: str,
        existing_ui: str,
        conversation_history: str,
    ) -> str:

        return f"""
You are ZenUI's Context Intelligence Engine.

Your job is to determine whether the current request
depends on an existing interface or previous conversation.

Do NOT generate UI.

Do NOT answer the user.

Return JSON only.

Possible operations:

create
modify
add
remove
replace
refresh
explain
navigate
unknown

--------------------------------------------------
CURRENT USER REQUEST
--------------------------------------------------

{user_prompt}

--------------------------------------------------
EXISTING UI
--------------------------------------------------

{existing_ui}

--------------------------------------------------
CONVERSATION
--------------------------------------------------

{conversation_history}

--------------------------------------------------
RETURN
--------------------------------------------------

{{
    "operation": "create",
    "target_component": null,
    "context_used": false,
    "context_summary": null,
    "relevant_components": []
}}

Rules:

1. Use "create" when this is a new interface.

2. Use "modify", "remove", "replace", "add",
   or "refresh" when the user is referring to
   an existing interface.

3. target_component should identify an existing
   component when possible.

4. context_used should be true only when the
   previous UI or conversation matters.

5. Never invent component IDs.

Return valid JSON only.
"""

    # ========================================================
    # NORMALIZE UI STATE
    # ========================================================

    @staticmethod
    def _normalize_ui_state(
        value: Any,
    ) -> Optional[UIState]:

        if value is None:

            return None

        if isinstance(
            value,
            UIState,
        ):

            return value

        # ----------------------------------------------------
        # UIPlan dictionary
        # ----------------------------------------------------

        if isinstance(
            value,
            dict,
        ):

            components = (
                value.get(
                    "components",
                    []
                )
            )

            if not isinstance(
                components,
                list,
            ):

                components = []

            normalized: list[
                UIComponent
            ] = []

            for component in components:

                if not isinstance(
                    component,
                    dict,
                ):

                    continue

                normalized.append(
                    UIComponent(
                        id=str(
                            component.get(
                                "id",
                                "",
                            )
                        ),
                        type=str(
                            component.get(
                                "type",
                                "unknown",
                            )
                        ),
                        label=(
                            component.get(
                                "label"
                            )
                            or component.get(
                                "props",
                                {},
                            ).get(
                                "label"
                            )
                            if isinstance(
                                component.get(
                                    "props",
                                    {},
                                ),
                                dict,
                            )
                            else None
                        ),
                        properties=(
                            component.get(
                                "props",
                                {},
                            )
                            if isinstance(
                                component.get(
                                    "props",
                                    {},
                                ),
                                dict,
                            )
                            else {}
                        ),
                    )
                )

            return UIState(
                components=normalized
            )

        # ----------------------------------------------------
        # Pydantic UIPlan
        # ----------------------------------------------------

        if hasattr(
            value,
            "model_dump",
        ):

            try:

                return ContextAnalyzer._normalize_ui_state(
                    value.model_dump()
                )

            except Exception:

                return None

        return None

    # ========================================================
    # SERIALIZATION
    # ========================================================

    @staticmethod
    def _serialize_ui_state(
        ui_state: Optional[UIState],
    ) -> str:

        if ui_state is None:

            return "No existing UI."

        if not ui_state.components:

            return "Existing UI is empty."

        return json.dumps(
            ui_state.model_dump(),
            indent=2,
        )

    @staticmethod
    def _serialize_history(
        conversation_history: Optional[list[Any]],
    ) -> str:

        if not conversation_history:

            return "No previous conversation."

        serializable = []

        for item in conversation_history:

            if isinstance(
                item,
                dict,
            ):

                serializable.append(
                    item
                )

            elif hasattr(
                item,
                "model_dump",
            ):

                try:

                    serializable.append(
                        item.model_dump()
                    )

                except Exception:

                    continue

        return json.dumps(
            serializable,
            indent=2,
            default=str,
        )

    # ========================================================
    # JSON
    # ========================================================

    @staticmethod
    def _parse_json(
        raw_response: str | None,
    ) -> dict[str, Any]:

        if not raw_response:

            return {}

        text = raw_response.strip()

        if text.startswith("```"):

            text = (
                text.replace(
                    "```json",
                    "",
                )
                .replace(
                    "```",
                    "",
                )
                .strip()
            )

        try:

            result = json.loads(
                text
            )

            return (
                result
                if isinstance(
                    result,
                    dict,
                )
                else {}
            )

        except json.JSONDecodeError:

            start = text.find("{")
            end = text.rfind("}")

            if (
                start == -1
                or end == -1
                or end <= start
            ):

                return {}

            try:

                result = json.loads(
                    text[
                        start : end + 1
                    ]
                )

                return (
                    result
                    if isinstance(
                        result,
                        dict,
                    )
                    else {}
                )

            except json.JSONDecodeError:

                return {}