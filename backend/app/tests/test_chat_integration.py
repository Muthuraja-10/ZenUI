from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.api.chat import orchestrator
from app.intelligence.orchestrator import OrchestratorResult


# ============================================================
# TEST CLIENT
# ============================================================

client = TestClient(app)


# ============================================================
# FAKE ORCHESTRATOR
# ============================================================

class FakeOrchestrator:
    """
    Deterministic orchestrator used only for API integration tests.

    This prevents the test from depending on:
        - Groq
        - Serper
        - Linkup
        - external network
    """

    async def process(
        self,
        user_prompt: str,
        session_id: str = "default",
    ) -> OrchestratorResult:

        refined = (
            "remove" in user_prompt.lower()
            or "change" in user_prompt.lower()
            or "modify" in user_prompt.lower()
        )

        return OrchestratorResult(
            ui=(
                "root = Stack([heading, data_table])"
            ),
            ui_plan={
                "root_components": [
                    "heading",
                    "data_table",
                ],
                "components": [
                    {
                        "id": "heading",
                        "type": "heading",
                        "props": {
                            "text": "Purchase Orders",
                        },
                    },
                    {
                        "id": "data_table",
                        "type": "table",
                        "props": {
                            "columns": [
                                {
                                    "key": "po_number",
                                    "label": "PO Number",
                                },
                                {
                                    "key": "amount",
                                    "label": "Amount",
                                },
                            ],
                            "rows": [
                                {
                                    "po_number": "PO-1001",
                                    "amount": 125000,
                                },
                            ],
                        },
                    },
                ],
                "metadata": {
                    "refined": refined,
                },
            },
            resource_data={
                "purchase_orders": [
                    {
                        "po_number": "PO-1001",
                        "amount": 125000,
                        "status": "Approved",
                    }
                ]
            },
            tool_calls=[
                {
                    "tool_name": "internal_resource",
                    "arguments": {
                        "resource_type": "purchase_orders",
                    },
                }
            ],
            tool_results=[
                {
                    "success": True,
                    "data": {
                        "purchase_orders": [
                            {
                                "po_number": "PO-1001",
                                "amount": 125000,
                                "status": "Approved",
                            }
                        ]
                    },
                    "error": None,
                }
            ],
        )


# ============================================================
# MAIN INTEGRATION TEST
# ============================================================

def test_chat_integration():

    print()
    print("=" * 70)
    print("ZENUI CHAT INTEGRATION TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # Replace real orchestrator
    # --------------------------------------------------------

    original_orchestrator = app_orchestrator = orchestrator

    import app.api.chat as chat_module

    chat_module.orchestrator = FakeOrchestrator()

    try:

        # ====================================================
        # 1. INITIAL CHAT REQUEST
        # ====================================================

        print()
        print("[1] INITIAL CHAT REQUEST")

        response = client.post(
            "/api/chat",
            json={
                "message": "Show purchase orders",
                "session_id": "integration-test",
            },
        )

        print("STATUS:", response.status_code)
        print("RESPONSE:", response.json())

        assert response.status_code == 200

        data = response.json()

        assert data["session_id"] == "integration-test"

        assert (
            data["message"]
            == "Generated interface successfully."
        )

        assert data["ui"]

        assert isinstance(
            data["ui_plan"],
            dict,
        )

        assert isinstance(
            data["resource_data"],
            dict,
        )

        assert isinstance(
            data["tool_calls"],
            list,
        )

        assert isinstance(
            data["tool_results"],
            list,
        )

        print("PASS — initial chat")


        # ====================================================
        # 2. UI RESPONSE
        # ====================================================

        print()
        print("[2] UI RESPONSE")

        assert (
            "Stack"
            in data["ui"]
        )

        assert (
            "data_table"
            in data["ui"]
        )

        print("PASS — OpenUI returned")


        # ====================================================
        # 3. UI PLAN
        # ====================================================

        print()
        print("[3] UI PLAN")

        components = (
            data["ui_plan"]
            .get("components", [])
        )

        assert len(components) > 0

        component_types = [
            component["type"]
            for component in components
        ]

        assert "heading" in component_types
        assert "table" in component_types

        print(
            "COMPONENTS:",
            component_types,
        )

        print("PASS — UI plan")


        # ====================================================
        # 4. RESOURCE DATA
        # ====================================================

        print()
        print("[4] RESOURCE DATA")

        resource_data = (
            data["resource_data"]
        )

        assert (
            "purchase_orders"
            in resource_data
        )

        assert (
            resource_data[
                "purchase_orders"
            ][0]["po_number"]
            == "PO-1001"
        )

        print("PASS — resource data")


        # ====================================================
        # 5. TOOL DATA
        # ====================================================

        print()
        print("[5] TOOL DATA")

        assert len(
            data["tool_calls"]
        ) > 0

        assert len(
            data["tool_results"]
        ) > 0

        print("PASS — tool calls/results")


        # ====================================================
        # 6. REFINED REQUEST
        # ====================================================

        print()
        print("[6] REFINED REQUEST")

        response = client.post(
            "/api/chat",
            json={
                "message": "Change the purchase orders",
                "session_id": "integration-test",
            },
        )

        print(
            "STATUS:",
            response.status_code,
        )

        assert response.status_code == 200

        refined_data = response.json()

        assert (
            refined_data["message"]
            == "Updated interface."
        )

        assert (
            refined_data["ui_plan"]
            ["metadata"]
            ["refined"]
            is True
        )

        print("PASS — modification response")


        # ====================================================
        # 7. DEFAULT SESSION
        # ====================================================

        print()
        print("[7] DEFAULT SESSION")

        response = client.post(
            "/api/chat",
            json={
                "message": "Show purchase orders",
            },
        )

        assert response.status_code == 200

        default_data = response.json()

        assert (
            default_data["session_id"]
            == "default"
        )

        print("PASS — default session")


        # ====================================================
        # 8. EMPTY MESSAGE
        # ====================================================

        print()
        print("[8] EMPTY MESSAGE")

        response = client.post(
            "/api/chat",
            json={
                "message": "",
                "session_id": "integration-test",
            },
        )

        print(
            "STATUS:",
            response.status_code,
        )

        assert response.status_code == 400

        assert (
            response.json()["detail"]
            == "Message cannot be empty."
        )

        print("PASS — empty message validation")


        # ====================================================
        # 9. WHITESPACE MESSAGE
        # ====================================================

        print()
        print("[9] WHITESPACE MESSAGE")

        response = client.post(
            "/api/chat",
            json={
                "message": "   ",
                "session_id": "integration-test",
            },
        )

        assert response.status_code == 400

        print("PASS — whitespace validation")


        # ====================================================
        # 10. RESPONSE CONTRACT
        # ====================================================

        print()
        print("[10] RESPONSE CONTRACT")

        response = client.post(
            "/api/chat",
            json={
                "message": "Show purchase orders",
                "session_id": "contract-test",
            },
        )

        assert response.status_code == 200

        contract = response.json()

        required_fields = {
            "session_id",
            "message",
            "ui",
            "ui_plan",
            "resource_data",
            "tool_calls",
            "tool_results",
        }

        assert required_fields.issubset(
            contract.keys()
        )

        print(
            "FIELDS:",
            sorted(contract.keys()),
        )

        print("PASS — response contract")


        # ====================================================
        # COMPLETE
        # ====================================================

        print()
        print("=" * 70)
        print("ZENUI CHAT INTEGRATION TEST COMPLETE")
        print("=" * 70)

    finally:

        # Restore the real orchestrator
        chat_module.orchestrator = (
            original_orchestrator
        )