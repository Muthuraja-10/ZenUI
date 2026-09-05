import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_backend_standard():

    print("\n" + "=" * 70)
    print("ZENUI BACKEND STANDARD TEST")
    print("=" * 70)

    # ==========================================================
    # 1. CORE
    # ==========================================================

    print("\n[1] CORE")

    from app.core.config import settings

    assert settings.app_name == "ZenUI Enterprise"

    print("PASS — configuration")

    # ==========================================================
    # 2. COMPONENT REGISTRY
    # ==========================================================

    print("\n[2] COMPONENT REGISTRY")

    from app.intelligence.component_registry import (
        is_supported_component,
        supported_components,
        component_categories,
        get_component_definition,
    )

    assert is_supported_component("table")
    assert is_supported_component("bar_chart")
    assert is_supported_component("line_chart")
    assert is_supported_component("form")

    assert not is_supported_component("xyz_invalid")

    assert len(supported_components()) == 18

    assert "table" in component_categories()["data"]
    assert "bar_chart" in component_categories()["chart"]

    assert get_component_definition("table")
    assert get_component_definition("xyz_invalid") == {}

    print("PASS — component registry")

    # ==========================================================
    # 3. CONVERSATION
    # ==========================================================

    print("\n[3] CONVERSATION")

    from app.conversation.manager import ConversationManager

    manager = ConversationManager()

    session_id = "backend-standard-test"

    manager.clear(session_id)

    manager.add_user_message(
        session_id,
        "Show purchase orders",
    )

    state = manager.get_state(session_id)

    assert len(state.messages) == 1
    assert state.messages[0].role == "user"

    manager.add_assistant_message(
        session_id=session_id,
        content="Generated interface successfully.",
        ui="root = Stack([heading, table])",
        ui_plan={
            "components": [
                {
                    "id": "heading",
                    "type": "heading",
                }
            ]
        },
        resource_data={
            "purchase_orders": [
                {
                    "po_number": "PO-1001",
                    "amount": 125000,
                }
            ]
        },
    )

    assert manager.get_current_ui(session_id)
    assert manager.get_current_ui_plan(session_id)
    assert manager.get_current_resource_data(session_id)

    manager.clear(session_id)

    print("PASS — conversation")

    # ==========================================================
    # 4. INTELLIGENCE
    # ==========================================================

    print("\n[4] INTELLIGENCE")

    from app.intelligence.intent_analyzer import IntentAnalyzer
    from app.intelligence.context_analyzer import ContextAnalyzer
    from app.intelligence.resource_planner import ResourcePlanner
    from app.intelligence.planner import UIPlanner
    from app.intelligence.ui_modification import (
        UIModificationDetector,
    )
    from app.intelligence.ui_plan_modifier import (
        UIPlanModifier,
    )
    from app.intelligence.result_normalizer import (
        ResultNormalizer,
    )

    prompt = "Show purchase orders"

    # ----------------------------------------------------------
    # Intent
    # ----------------------------------------------------------

    intent = await IntentAnalyzer().analyze(prompt)

    assert intent.intent
    assert intent.domain == "procurement"
    assert intent.target == "purchase_order"

    print("PASS — intent analyzer")

    # ----------------------------------------------------------
    # Context
    # ----------------------------------------------------------

    context = await ContextAnalyzer().analyze(
        user_prompt=prompt,
    )

    assert context.operation == "create"
    assert context.has_existing_ui is False

    print("PASS — context analyzer")

    # ----------------------------------------------------------
    # Resource planner
    # ----------------------------------------------------------

    resource_plan = await ResourcePlanner().plan(
        user_prompt=prompt,
        intent=intent,
        context=context,
    )

    assert resource_plan.requires_data is True
    assert resource_plan.data_source == "purchase_orders"
    assert resource_plan.operation == "list"

    print("PASS — resource planner")

    # ----------------------------------------------------------
    # UI planner
    # ----------------------------------------------------------

    resource_data = {
        "purchase_orders": [
            {
                "po_number": "PO-1001",
                "vendor": "ABC Suppliers",
                "amount": 125000,
                "status": "Approved",
            },
            {
                "po_number": "PO-1002",
                "vendor": "XYZ Industries",
                "amount": 85000,
                "status": "Pending",
            },
        ]
    }

    ui_plan = UIPlanner().create_plan(
        intent=intent,
        resource_data=resource_data,
        user_prompt=prompt,
        context=context,
    )

    assert ui_plan
    assert ui_plan.components

    component_types = [
        component.type
        for component in ui_plan.components
    ]

    assert "heading" in component_types
    assert "table" in component_types

    print("PASS — UI planner")

    # ----------------------------------------------------------
    # UI modification detector
    # ----------------------------------------------------------

    modification = UIModificationDetector().detect(
        "remove Status column"
    )

    assert modification.is_modification is True
    assert modification.action == "remove_column"
    assert modification.target == "status"

    print("PASS — modification detector")

    # ----------------------------------------------------------
    # UI plan modifier
    # ----------------------------------------------------------

    ui_plan_dict = ui_plan.model_dump()

    modified_plan = UIPlanModifier().modify(
        ui_plan=ui_plan_dict,
        modification=modification,
        resource_data=resource_data,
    )

    assert modified_plan is not None

    table_components = [
        component
        for component in modified_plan["components"]
        if component["type"] == "table"
    ]

    assert table_components

    columns = table_components[0]["props"]["columns"]

    column_keys = [
        column["key"]
        for column in columns
    ]

    assert "status" not in column_keys

    print("PASS — UI plan modifier")

    # ----------------------------------------------------------
    # Result normalizer
    # ----------------------------------------------------------

    normalized = await ResultNormalizer().normalize(
        user_prompt=prompt,
        intent=intent,
        tool_name="internal_resource",
        tool_data=resource_data,
    )

    assert normalized
    assert normalized["source"] == "internal_resource"
    assert normalized["records"]

    print("PASS — result normalizer")

    # ==========================================================
    # 5. OPENUI
    # ==========================================================

    print("\n[5] OPENUI")

    from app.openui.generator import OpenUIGenerator

    generator = OpenUIGenerator()

    ui = generator.generate(ui_plan)

    assert isinstance(ui, str)
    assert len(ui.strip()) > 0

    assert "Stack" in ui
    assert "Table" in ui

    chart_plan = UIPlanModifier().modify(
        ui_plan=ui_plan.model_dump(),
        modification=UIModificationDetector().detect(
            "add a bar chart"
        ),
        resource_data=resource_data,
    )

    assert chart_plan is not None
    chart = next(
        component
        for component in chart_plan["components"]
        if component["type"] == "bar_chart"
    )
    assert chart["props"]["series"][0]["values"] == [
        125000.0,
        85000.0,
    ]

    chart_ui = generator.generate(chart_plan)
    assert "BarChart" in chart_ui
    assert "125000" in chart_ui
    assert "85000" in chart_ui

    print("PASS — OpenUI generator")

    # ==========================================================
    # 6. LLM SERVICE
    # ==========================================================

    print("\n[6] LLM SERVICE")

    from app.llm.llm_service import LLMService

    # Do not make a real API call here.
    # Verify that the service class exposes
    # the expected interface.

    assert hasattr(LLMService, "generate")
    assert hasattr(LLMService, "generate_json")

    print("PASS — LLM service interface")

    # ==========================================================
    # 7. ORCHESTRATOR
    # ==========================================================

    print("\n[7] ORCHESTRATOR")

    from app.intelligence.orchestrator import (
        ZenUIOrchestrator,
        OrchestratorResult,
    )

    orchestrator = ZenUIOrchestrator()

    assert hasattr(orchestrator, "process")
    assert callable(orchestrator.process)

    print("PASS — orchestrator interface")

    # ==========================================================
    # 8. FASTAPI
    # ==========================================================

    print("\n[8] FASTAPI")

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # ----------------------------------------------------------
    # Root
    # ----------------------------------------------------------

    response = client.get("/")

    assert response.status_code == 200

    root_data = response.json()

    assert root_data["name"] == "ZenUI Enterprise"
    assert root_data["status"] == "running"

    print("PASS — root endpoint")

    # ==========================================================
    # REGRESSION: CONTEXT SAFETY
    # ==========================================================

    print("\n[REGRESSION] CONTEXT SAFETY")

    from app.conversation.manager import ConversationManager
    from app.intelligence.context_analyzer import ContextAnalyzer
    from app.intelligence.orchestrator import ZenUIOrchestrator

    manager = ConversationManager()
    session_id = "context-safety-regression"
    manager.clear(session_id)

    manager.add_assistant_message(
        session_id=session_id,
        content="Generated interface successfully.",
        ui="root = Stack([heading, table])",
        ui_plan={
            "root_components": ["heading", "data_table"],
            "components": [
                {"id": "heading", "type": "heading", "props": {"text": "Purchase Orders"}},
                {"id": "data_table", "type": "table", "props": {"rows": [{"po_number": "PO-1001", "amount": 100}]}} ,
            ],
        },
        resource_data={
            "purchase_orders": [{"po_number": "PO-1001", "amount": 100}],
        },
    )

    analyzer = ContextAnalyzer()
    original_generate = analyzer.llm.generate

    async def boom(*args, **kwargs):
        raise RuntimeError("simulated rate limit")

    analyzer.llm.generate = boom

    try:
        result = await analyzer.analyze(
            user_prompt="What is OpenUI?",
            ui_state={"components": [{"id": "heading", "type": "heading"}]},
            conversation_history=[{"role": "user", "content": "Show purchase orders"}],
        )
        assert result.operation == "create"
        assert result.context_used is False
    finally:
        analyzer.llm.generate = original_generate

    orchestrator = ZenUIOrchestrator()
    original_analyze = orchestrator.context_analyzer.analyze

    async def fail_safe(*args, **kwargs):
        raise RuntimeError("simulated rate limit")

    orchestrator.context_analyzer.analyze = fail_safe

    try:
        first = await orchestrator.process("Show purchase orders", session_id)
        second = await orchestrator.process("What is OpenUI?", session_id)
        assert "purchase_orders" not in second.resource_data
    finally:
        orchestrator.context_analyzer.analyze = original_analyze
        manager.clear(session_id)

    print("PASS — context safety regression")

    # ==========================================================
    # EXTERNAL / GREETING REGRESSIONS
    # ==========================================================

    analyzer = IntentAnalyzer()

    greeting = await analyzer.analyze("Hello")
    capability = await analyzer.analyze("What can you do?")

    assert greeting.intent == "greeting"
    assert capability.intent == "capability_query"

    from app.tools.tool_agent import ToolAgent

    agent = ToolAgent()
    assert agent._fallback_tool_selection(
        "Hello",
        greeting.model_dump(),
    ) is None

    external_data = {
        "source": "serper",
        "summary": "OpenUI is a declarative UI language.",
        "records": [
            {
                "title": "OpenUI documentation",
                "snippet": "Reference documentation",
                "source": "https://openui.dev",
            }
        ],
        "sources": [
            {
                "title": "OpenUI documentation",
                "url": "https://openui.dev",
            }
        ],
        "metadata": {
            "external": True,
        },
    }

    external_plan = UIPlanner().create_plan(
        intent={
            "intent": "general_information",
            "operation": "search",
            "requested_output": "information",
            "requested_components": ["text"],
        },
        user_prompt="What is OpenUI?",
        resource_data=external_data,
    )

    external_types = [
        component.type
        for component in external_plan.components
    ]

    assert "text" in external_types
    assert "table" not in external_types
    assert "openui.dev" in external_plan.components[0].props.get(
        "text",
        "",
    ) or any(
        "openui.dev" in component.props.get("text", "")
        for component in external_plan.components
    )

    empty_plan = UIPlanner().create_plan(
        intent={
            "intent": "general_information",
            "operation": "search",
            "requested_output": "information",
            "requested_components": ["text"],
        },
        user_prompt="Find OpenUI documentation",
        resource_data={
            "metadata": {
                "empty": True,
            }
        },
    )

    assert any(
        "No relevant information" in component.props.get(
            "text",
            "",
        )
        for component in empty_plan.components
    )

    # ----------------------------------------------------------
    # CONVERSATIONAL UI EDITING MATRIX
    # ----------------------------------------------------------

    editing_plan = {
        "root_components": [
            "heading",
            "data_table",
            "bar_chart",
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
                            "key": "amount",
                            "label": "Amount",
                        },
                        {
                            "key": "status",
                            "label": "Status",
                        },
                    ],
                    "rows": [
                        {
                            "amount": 100,
                            "status": "Pending",
                        },
                        {
                            "amount": 300,
                            "status": "Approved",
                        },
                        {
                            "amount": 200,
                            "status": "Pending",
                        },
                    ],
                },
            },
            {
                "id": "bar_chart",
                "type": "bar_chart",
                "props": {
                    "labels": ["A"],
                    "series": [
                        {
                            "name": "Amount",
                            "values": [1],
                        }
                    ],
                },
            },
        ],
    }

    detector = UIModificationDetector()
    modifier = UIPlanModifier()

    removed = modifier.modify(
        editing_plan,
        detector.detect("remove it"),
    )
    assert removed is not None
    assert all(
        component["type"] != "bar_chart"
        for component in removed["components"]
    )

    replaced = modifier.modify(
        editing_plan,
        detector.detect("change it to a pie chart"),
    )
    assert replaced is not None
    assert any(
        component["type"] == "pie_chart"
        for component in replaced["components"]
    )

    renamed = modifier.modify(
        editing_plan,
        detector.detect(
            "rename amount column to total amount"
        ),
    )
    assert renamed is not None
    assert renamed["components"][1]["props"]["columns"][0]["key"] == "total_amount"

    filtered = modifier.modify(
        editing_plan,
        detector.detect("show only pending orders"),
    )
    assert filtered is not None
    assert len(filtered["components"][1]["props"]["rows"]) == 2

    sorted_plan = modifier.modify(
        editing_plan,
        detector.detect("sort by amount highest first"),
    )
    assert sorted_plan is not None
    assert sorted_plan["components"][1]["props"]["rows"][0]["amount"] == 300

    # ----------------------------------------------------------
    # Health
    # ----------------------------------------------------------

    response = client.get("/health")

    assert response.status_code == 200

    health_data = response.json()

    assert health_data["status"] == "healthy"
    assert health_data["service"] == "zenui-backend"

    print("PASS — health endpoint")

    # ==========================================================
    # COMPLETE
    # ==========================================================

    print("\n" + "=" * 70)
    print("ZENUI BACKEND STANDARD TEST COMPLETE")
    print("=" * 70)