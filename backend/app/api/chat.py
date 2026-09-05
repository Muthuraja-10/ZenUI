from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
)

from pydantic import (
    BaseModel,
    Field,
)

from app.intelligence.orchestrator import (
    ZenUIOrchestrator,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api",
    tags=["chat"],
)


# ============================================================
# REQUEST
# ============================================================


class ChatRequest(BaseModel):

    message: str

    session_id: str = "default"


# ============================================================
# RESPONSE
# ============================================================


class ChatResponse(BaseModel):

    session_id: str

    message: str = (
        "Generated interface successfully."
    )

    ui: str

    ui_plan: dict[str, Any] = Field(
        default_factory=dict
    )

    resource_data: dict[str, Any] = Field(
        default_factory=dict
    )

    tool_calls: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )

    tool_results: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )


# ============================================================
# ORCHESTRATOR
# ============================================================

orchestrator = (
    ZenUIOrchestrator()
)


# ============================================================
# CHAT
# ============================================================


@router.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
):

    message = (
        request.message or ""
    ).strip()

    if not message:

        raise HTTPException(
            status_code=400,
            detail=(
                "Message cannot be empty."
            ),
        )

    session_id = (
        request.session_id or "default"
    ).strip()

    try:

        result = (
            await orchestrator.process(
                user_prompt=message,
                session_id=session_id,
            )
        )

        return ChatResponse(
            session_id=session_id,

            message=(
                "Updated interface."
                if result.ui_plan.get(
                    "metadata",
                    {},
                ).get(
                    "refined",
                    False,
                )
                else
                "Generated interface successfully."
            ),

            ui=result.ui,

            ui_plan=result.ui_plan,

            resource_data=(
                result.resource_data
            ),

            tool_calls=(
                result.tool_calls
            ),

            tool_results=(
                result.tool_results
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        print(
            "\n========== CHAT ERROR =========="
        )

        print(
            repr(exc)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "ZenUI failed to process "
                "the request."
            ),
        )