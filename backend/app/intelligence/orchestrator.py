from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.conversation.manager import conversation_manager

from app.intelligence.context_analyzer import ContextAnalyzer
from app.intelligence.intent_analyzer import IntentAnalyzer
from app.intelligence.planner import UIPlan, UIPlanner
from app.intelligence.result_normalizer import ResultNormalizer
from app.intelligence.ui_modification import UIModificationDetector
from app.intelligence.ui_plan_modifier import UIPlanModifier

from app.openui.generator import OpenUIGenerator

from app.tools.tool_agent import ToolAgent


# ============================================================
# RESULT
# ============================================================


class OrchestratorResult(BaseModel):
    """
    Final result produced by the ZenUI orchestration pipeline.
    """

    ui: str

    ui_plan: dict[str, Any] = Field(
        default_factory=dict
    )

    resource_data: dict[str, Any] = Field(
        default_factory=dict
    )

    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list
    )

    tool_results: list[dict[str, Any]] = Field(
        default_factory=list
    )


# ============================================================
# ORCHESTRATOR
# ============================================================


class ZenUIOrchestrator:
    """
    Coordinates the complete ZenUI pipeline.

    The orchestrator does NOT contain:

    - business-domain knowledge
    - purchase-order data
    - CRUD implementation
    - UI component definitions
    - resource-specific logic

    Those responsibilities belong to their respective layers.

    Pipeline:

        request
            ↓
        context
            ↓
        modification detection
            ↓
        intent
            ↓
        tool execution
            ↓
        result normalization
            ↓
        UI planning/modification
            ↓
        OpenUI generation
            ↓
        conversation persistence
    """

    def __init__(self) -> None:

        self.context_analyzer = ContextAnalyzer()

        self.intent_analyzer = IntentAnalyzer()

        self.tool_agent = ToolAgent()

        self.result_normalizer = ResultNormalizer()

        self.ui_planner = UIPlanner()

        self.modification_detector = (
            UIModificationDetector()
        )

        self.ui_plan_modifier = UIPlanModifier()

        self.openui_generator = OpenUIGenerator()

    # ========================================================
    # PUBLIC PROCESS
    # ========================================================

    async def process(
        self,
        user_prompt: str,
        session_id: str = "default",
    ) -> OrchestratorResult:

        user_prompt = (
            user_prompt or ""
        ).strip()

        if not user_prompt:
            raise ValueError(
                "User prompt cannot be empty."
            )

        # ====================================================
        # 1. LOAD CONVERSATION STATE
        # ====================================================

        history = (
            conversation_manager.get_history(
                session_id
            )
        )

        previous_ui = (
            conversation_manager.get_current_ui(
                session_id
            )
        )

        previous_ui_plan = (
            conversation_manager.get_current_ui_plan(
                session_id
            )
        )

        previous_resource_data = (
            conversation_manager.get_current_resource_data(
                session_id
            )
        )

        # ====================================================
        # 2. RECOVER UI STATE ONLY WHEN NECESSARY
        # ====================================================

        if not previous_ui_plan:
            previous_ui_plan = (
                self._get_previous_ui_plan(
                    history
                )
            )

        if not previous_ui:
            previous_ui = (
                self._get_previous_ui(
                    history
                )
            )

        # ----------------------------------------------------
        # IMPORTANT
        #
        # We intentionally DO NOT recover resource data from
        # history here.
        #
        # A new request must obtain fresh data through ToolAgent.
        #
        # Resource data is only reused later if the request is
        # confirmed as a modification of the current interface.
        # ----------------------------------------------------

        if not isinstance(
            previous_resource_data,
            dict,
        ):
            previous_resource_data = {}

        # ====================================================
        # 3. CONTEXT ANALYSIS
        # ====================================================

        context = None

        try:

            context = (
                await self.context_analyzer.analyze(
                    user_prompt=user_prompt,
                    ui_state=previous_ui_plan,
                    conversation_history=history,
                )
            )

        except Exception as error:

            print(
                "Context analyzer failed:",
                error,
            )

        # ====================================================
        # 4. EXPLICIT UI MODIFICATION DETECTION
        # ====================================================

        modification = (
            self.modification_detector.detect(
                user_prompt
            )
        )

        # ====================================================
        # 5. RESOLVE REQUEST MODE
        # ====================================================

        has_previous_ui = bool(
            isinstance(
                previous_ui_plan,
                dict,
            )
            and previous_ui_plan.get(
                "components"
            )
        )

        explicit_modification = bool(
            getattr(
                modification,
                "is_modification",
                False,
            )
        )

        context_used = bool(
            getattr(
                context,
                "context_used",
                False,
            )
        )

        context_operation = str(
            getattr(
                context,
                "operation",
                "",
            )
            or ""
        ).strip().lower()

        # ----------------------------------------------------
        # Context is considered a modification signal only when
        # an existing UI actually exists.
        #
        # "create" means the current request is not asking to
        # modify the existing interface.
        #
        # We do not maintain a domain-specific CRUD list here.
        # ----------------------------------------------------

        context_modification = (
            has_previous_ui
            and context_used
            and context_operation
            and context_operation != "create"
        )

        is_modification = (
            has_previous_ui
            and (
                explicit_modification
                or context_modification
            )
        )

        # ====================================================
        # 6. SAVE CURRENT USER MESSAGE
        # ====================================================

        conversation_manager.add_user_message(
            session_id=session_id,
            content=user_prompt,
        )

        # ====================================================
        # 7. INTENT ANALYSIS
        # ====================================================

        try:

            intent = (
                await self.intent_analyzer.analyze(
                    user_prompt
                )
            )

            intent_data = (
                self._model_to_dict(
                    intent
                )
            )

        except Exception as error:

            print(
                "Intent analyzer failed:",
                error,
            )

            intent_data = {
                "intent": "unknown",
                "domain": None,
                "operation": "unknown",
                "target": None,
                "entities": [],
                "metrics": [],
                "filters": [],
                "time_range": None,
                "location": None,
                "requested_output": None,
                "requested_components": [],
                "confidence": 0.0,
            }

        # ====================================================
        # 8. BUILD PIPELINE CONTEXT
        # ====================================================

        intent_data["raw_text"] = user_prompt

        intent_data["conversation_history"] = history

        intent_data["previous_ui_plan"] = (
            previous_ui_plan
            if is_modification
            else {}
        )

        intent_data["previous_ui"] = (
            previous_ui
            if is_modification
            else None
        )

        # ====================================================
        # 9. MODIFICATION PATH
        # ====================================================

        if is_modification:

            return await self._process_modification(
                user_prompt=user_prompt,
                session_id=session_id,
                history=history,
                previous_ui=previous_ui,
                previous_ui_plan=previous_ui_plan,
                previous_resource_data=previous_resource_data,
                intent_data=intent_data,
                context=context,
                modification=modification,
            )

        # ====================================================
        # 10. NEW REQUEST PATH
        # ====================================================

        return await self._process_new_request(
            user_prompt=user_prompt,
            session_id=session_id,
            history=history,
            intent_data=intent_data,
            context=context,
        )

    # ========================================================
    # NEW REQUEST
    # ========================================================

    async def _process_new_request(
        self,
        user_prompt: str,
        session_id: str,
        history: list[Any],
        intent_data: dict[str, Any],
        context: Any,
    ) -> OrchestratorResult:

        """
        Process a completely new request.

        Previous UI and previous resource data are NOT passed
        into the planner.

        Fresh data must come from ToolAgent.
        """

        print()
        print(
            "========== ZENUI NEW REQUEST =========="
        )

        # ====================================================
        # 1. TOOL EXECUTION
        # ====================================================

        tool_result = None

        try:

            tool_result = (
                await self.tool_agent.run(
                    user_prompt=user_prompt,
                    intent=intent_data,
                )
            )

        except Exception as error:

            print(
                "Tool agent failed:",
                error,
            )

        # ====================================================
        # 2. EXTRACT TOOL DATA
        # ====================================================

        tool_calls: list[
            dict[str, Any]
        ] = []

        tool_results: list[
            dict[str, Any]
        ] = []

        resource_data: dict[
            str,
            Any,
        ] = {}

        if tool_result is not None:

            tool_calls = (
                self._model_list_to_dicts(
                    getattr(
                        tool_result,
                        "tool_calls",
                        [],
                    )
                )
            )

            tool_results = (
                self._model_list_to_dicts(
                    getattr(
                        tool_result,
                        "results",
                        [],
                    )
                )
            )

            # =================================================
            # Normalize successful tool results
            # =================================================

            raw_results = getattr(
                tool_result,
                "results",
                [],
            )

            if isinstance(
                raw_results,
                list,
            ):

                for result in raw_results:

                    if not getattr(
                        result,
                        "success",
                        False,
                    ):
                        continue

                    raw_data = getattr(
                        result,
                        "data",
                        {},
                    )

                    if not isinstance(
                        raw_data,
                        dict,
                    ):
                        continue

                    tool_name = str(
                        getattr(
                            result,
                            "tool_name",
                            "",
                        )
                        or ""
                    ).strip()

                    try:

                        normalized = (
                            await self.result_normalizer.normalize(
                                user_prompt=user_prompt,
                                intent=intent_data,
                                tool_name=tool_name,
                                tool_data=raw_data,
                            )
                        )

                        if isinstance(
                            normalized,
                            dict,
                        ):
                            resource_data = normalized

                        else:
                            resource_data = raw_data

                    except Exception as error:

                        print(
                            "Result normalization failed:",
                            error,
                        )

                        resource_data = raw_data

                    # The first successful resource is the
                    # primary normalized result.
                    #
                    # ToolAgent remains responsible for deciding
                    # which tools need to execute.
                    break

            # ------------------------------------------------
            # Compatibility fallback
            # ------------------------------------------------

            if not resource_data:

                direct_data = getattr(
                    tool_result,
                    "data",
                    {},
                )

                if isinstance(
                    direct_data,
                    dict,
                ):
                    resource_data = direct_data

        if not resource_data:
            resource_data = await self.result_normalizer.normalize(
                user_prompt=user_prompt,
                intent=intent_data,
                tool_name="unknown",
                tool_data=None,
            )

        # ====================================================
        # 3. PLAN NEW UI
        # ====================================================

        ui_plan = (
            self.ui_planner.create_plan(
                user_prompt=user_prompt,
                intent=intent_data,
                resource_data=resource_data,
                conversation_history=history,
                previous_ui_plan={},
                context=context,
            )
        )

        self._validate_ui_plan(
            ui_plan
        )

        # ====================================================
        # 4. GENERATE OPENUI
        # ====================================================

        ui = (
            self.openui_generator.generate(
                ui_plan
            )
        )

        self._validate_ui(
            ui
        )

        # ====================================================
        # 5. SAVE STATE
        # ====================================================

        ui_plan_dict = (
            ui_plan.model_dump()
        )

        conversation_manager.add_assistant_message(
            session_id=session_id,
            content=(
                "Generated interface successfully."
            ),
            ui=ui,
            ui_plan=ui_plan_dict,
            resource_data=resource_data,
        )

        # ====================================================
        # 6. RETURN
        # ====================================================

        return OrchestratorResult(
            ui=ui,
            ui_plan=ui_plan_dict,
            resource_data=resource_data,
            tool_calls=tool_calls,
            tool_results=self._safe_tool_results(
                tool_results
            ),
        )

    # ========================================================
    # MODIFICATION
    # ========================================================

    async def _process_modification(
        self,
        user_prompt: str,
        session_id: str,
        history: list[Any],
        previous_ui: str | None,
        previous_ui_plan: dict[str, Any],
        previous_resource_data: dict[str, Any],
        intent_data: dict[str, Any],
        context: Any,
        modification: Any,
    ) -> OrchestratorResult:

        """
        Process a conversational modification of the existing UI.

        Existing UI state is intentionally preserved.

        CRUD execution will later enter through ToolAgent rather
        than being implemented inside this method.
        """

        print()
        print(
            "========== ZENUI MODIFICATION =========="
        )

        # ====================================================
        # CURRENT RESOURCE STATE
        # ====================================================

        resource_data = (
            previous_resource_data
            if isinstance(
                previous_resource_data,
                dict,
            )
            and getattr(
                modification,
                "is_modification",
                False,
            )
            else {}
        )

        # ====================================================
        # TARGETED UI MODIFICATION
        # ====================================================

        modified_plan = None

        if getattr(
            modification,
            "is_modification",
            False,
        ):

            try:

                modified_plan = (
                    self.ui_plan_modifier.modify(
                        ui_plan=previous_ui_plan,
                        modification=modification,
                        resource_data=resource_data,
                    )
                )

            except Exception as error:

                print(
                    "UI plan modifier failed:",
                    error,
                )

        # ====================================================
        # FALLBACK TO INTELLIGENT PLANNING
        # ====================================================

        if modified_plan is not None:

            ui_plan = UIPlan.model_validate(
                modified_plan
            )

        else:

            ui_plan = (
                self.ui_planner.create_plan(
                    user_prompt=user_prompt,
                    intent=intent_data,
                    resource_data=resource_data,
                    conversation_history=history,
                    previous_ui_plan=previous_ui_plan,
                    context=context,
                )
            )

        # ====================================================
        # VALIDATE
        # ====================================================

        self._validate_ui_plan(
            ui_plan
        )

        # ====================================================
        # OPENUI
        # ====================================================

        ui = (
            self.openui_generator.generate(
                ui_plan
            )
        )

        self._validate_ui(
            ui
        )

        # ====================================================
        # SAVE
        # ====================================================

        ui_plan_dict = (
            ui_plan.model_dump()
        )

        conversation_manager.add_assistant_message(
            session_id=session_id,
            content="Updated interface",
            ui=ui,
            ui_plan=ui_plan_dict,
            resource_data=resource_data,
        )

        # ====================================================
        # RETURN
        # ====================================================

        return OrchestratorResult(
            ui=ui,
            ui_plan=ui_plan_dict,
            resource_data=resource_data,
            tool_calls=[],
            tool_results=[],
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    @staticmethod
    def _validate_ui_plan(
        ui_plan: Any,
    ) -> None:

        if not isinstance(
            ui_plan,
            UIPlan,
        ):
            raise TypeError(
                "UIPlanner must return UIPlan."
            )

    @staticmethod
    def _validate_ui(
        ui: Any,
    ) -> None:

        if not isinstance(
            ui,
            str,
        ) or not ui.strip():

            raise ValueError(
                "OpenUI generator returned empty UI."
            )

    # ========================================================
    # MODEL HELPERS
    # ========================================================

    @staticmethod
    def _model_to_dict(
        value: Any,
    ) -> dict[str, Any]:

        if isinstance(
            value,
            dict,
        ):
            return value

        if hasattr(
            value,
            "model_dump",
        ):

            try:

                result = (
                    value.model_dump()
                )

                if isinstance(
                    result,
                    dict,
                ):
                    return result

            except Exception:
                pass

        return {}

    @staticmethod
    def _model_list_to_dicts(
        values: Any,
    ) -> list[dict[str, Any]]:

        if not isinstance(
            values,
            list,
        ):
            return []

        result: list[
            dict[str, Any]
        ] = []

        for value in values:

            if isinstance(
                value,
                dict,
            ):

                result.append(
                    value
                )

                continue

            if hasattr(
                value,
                "model_dump",
            ):

                try:

                    dumped = (
                        value.model_dump()
                    )

                    if isinstance(
                        dumped,
                        dict,
                    ):

                        result.append(
                            dumped
                        )

                except Exception:
                    continue

        return result

    @staticmethod
    def _safe_tool_results(
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        safe_results = []

        for result in results:

            if not isinstance(result, dict):
                continue

            safe_result = dict(result)

            if not safe_result.get("success", False):
                safe_result["error"] = "Tool execution failed."

            safe_results.append(safe_result)

        return safe_results

    # ========================================================
    # HISTORY HELPERS
    # ========================================================

    @classmethod
    def _message_to_dict(
        cls,
        message: Any,
    ) -> dict[str, Any]:

        if isinstance(
            message,
            dict,
        ):
            return message

        if hasattr(
            message,
            "model_dump",
        ):

            try:

                dumped = (
                    message.model_dump()
                )

                if isinstance(
                    dumped,
                    dict,
                ):
                    return dumped

            except Exception:
                pass

        result: dict[
            str,
            Any,
        ] = {}

        for key in (
            "role",
            "content",
            "ui",
            "ui_plan",
            "resource_data",
        ):

            if hasattr(
                message,
                key,
            ):

                result[key] = getattr(
                    message,
                    key,
                )

        return result

    @classmethod
    def _get_previous_ui_plan(
        cls,
        history: Any,
    ) -> dict[str, Any]:

        if not isinstance(
            history,
            list,
        ):
            return {}

        for message in reversed(
            history
        ):

            data = (
                cls._message_to_dict(
                    message
                )
            )

            ui_plan = data.get(
                "ui_plan"
            )

            if (
                isinstance(
                    ui_plan,
                    dict,
                )
                and ui_plan.get(
                    "components"
                )
            ):

                return ui_plan

        return {}

    @classmethod
    def _get_previous_ui(
        cls,
        history: Any,
    ) -> str | None:

        if not isinstance(
            history,
            list,
        ):
            return None

        for message in reversed(
            history
        ):

            data = (
                cls._message_to_dict(
                    message
                )
            )

            ui = data.get(
                "ui"
            )

            if (
                isinstance(
                    ui,
                    str,
                )
                and ui.strip()
            ):

                return ui

        return None