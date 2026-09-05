from __future__ import annotations

from typing import Any

from app.conversation.models import (
    ConversationMessage,
    ConversationState,
)
from app.conversation.store import (
    conversation_store,
)


class ConversationManager:

    # ==========================================================
    # GET STATE
    # ==========================================================

    def get_state(
        self,
        session_id: str,
    ) -> ConversationState:

        return conversation_store.get_or_create(
            session_id
        )

    # ==========================================================
    # BUILD HISTORY
    # ==========================================================

    def get_history(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:

        state = self.get_state(
            session_id
        )

        return [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in state.messages
        ]

    # ==========================================================
    # ADD USER MESSAGE
    # ==========================================================

    def add_user_message(
        self,
        session_id: str,
        content: str,
    ) -> None:

        state = self.get_state(
            session_id
        )

        state.messages.append(
            ConversationMessage(
                role="user",
                content=content,
            )
        )

        conversation_store.save(
            state
        )

    # ==========================================================
    # ADD ASSISTANT MESSAGE
    # ==========================================================

    def add_assistant_message(
        self,
        session_id: str,
        content: str,
        ui: str,
        ui_plan: dict[str, Any],
        resource_data: dict[str, Any],
    ) -> None:

        state = self.get_state(
            session_id
        )

        state.messages.append(
            ConversationMessage(
                role="assistant",
                content=content,
                ui=ui,
                ui_plan=ui_plan,
                resource_data=resource_data,
            )
        )

        state.current_ui = ui

        state.current_ui_plan = (
            ui_plan
        )

        state.current_resource_data = (
            resource_data
        )

        conversation_store.save(
            state
        )

    # ==========================================================
    # CURRENT UI
    # ==========================================================

    def get_current_ui(
        self,
        session_id: str,
    ) -> str | None:

        state = self.get_state(
            session_id
        )

        return state.current_ui

    # ==========================================================
    # CURRENT UI PLAN
    # ==========================================================

    def get_current_ui_plan(
        self,
        session_id: str,
    ) -> dict[str, Any]:

        state = self.get_state(
            session_id
        )

        return state.current_ui_plan
    # ==========================================================
    # CURRENT RESOURCE DATA
    # ==========================================================

    def get_current_resource_data(
        self,
        session_id: str,
    ) -> dict[str, Any]:

        state = self.get_state(
            session_id
        )

        return state.current_resource_data

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(
        self,
        session_id: str,
    ) -> None:

        conversation_store.clear(
            session_id
        )


conversation_manager = ConversationManager()