from __future__ import annotations

from app.conversation.models import (
    ConversationState,
)


class ConversationStore:

    def __init__(self):

        self._sessions: dict[
            str,
            ConversationState,
        ] = {}

    # ==========================================================
    # GET / CREATE
    # ==========================================================

    def get_or_create(
        self,
        session_id: str,
    ) -> ConversationState:

        if session_id not in self._sessions:

            self._sessions[session_id] = (
                ConversationState(
                    session_id=session_id
                )
            )

        return self._sessions[session_id]

    # ==========================================================
    # SAVE
    # ==========================================================

    def save(
        self,
        state: ConversationState,
    ) -> None:

        self._sessions[
            state.session_id
        ] = state

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(
        self,
        session_id: str,
    ) -> None:

        self._sessions.pop(
            session_id,
            None,
        )


conversation_store = ConversationStore()