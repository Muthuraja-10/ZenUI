from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ============================================================
# RESOURCE PLAN
# ============================================================


class ResourcePlan(BaseModel):

    requires_data: bool = False

    data_source: str | None = None

    operation: str | None = None

    resource_type: str | None = None

    parameters: dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================
# RESOURCE PLANNER
# ============================================================


class ResourcePlanner:
    """
    Decides what resource data is required.

    This layer does NOT access the actual resource.

    Flow:

        User Request
             ↓
        ResourcePlanner
             ↓
        ResourcePlan
             ↓
        ResourceExecutor
             ↓
        Resource Data
    """

    async def plan(
        self,
        user_prompt: str,
        intent: Any = None,
        context: Any = None,
    ) -> ResourcePlan:

        text = (
            user_prompt or ""
        ).strip().lower()

        intent_name = self._get_intent(
            intent
        )

        # ====================================================
        # PURCHASE ORDERS
        # ====================================================

        if (
            "purchase order" in text
            or "purchase orders" in text
            or intent_name
            in {
                "purchase_orders",
                "purchase_order",
            }
        ):

            parameters: dict[str, Any] = {}

            if (
                "pending" in text
                and "approved" not in text
            ):

                parameters["status"] = "Pending"

            elif "approved" in text:

                parameters["status"] = "Approved"

            elif "rejected" in text:

                parameters["status"] = "Rejected"

            return ResourcePlan(
                requires_data=True,
                data_source="purchase_orders",
                operation="list",
                resource_type="purchase_orders",
                parameters=parameters,
            )

        # ====================================================
        # PURCHASE REQUESTS
        # ====================================================

        if (
            "purchase request" in text
            or "purchase requests" in text
            or intent_name
            in {
                "purchase_requests",
                "purchase_request",
            }
        ):

            parameters: dict[str, Any] = {}

            if "pending" in text:

                parameters["status"] = "Pending"

            elif "approved" in text:

                parameters["status"] = "Approved"

            elif "rejected" in text:

                parameters["status"] = "Rejected"

            return ResourcePlan(
                requires_data=True,
                data_source="purchase_requests",
                operation="list",
                resource_type="purchase_requests",
                parameters=parameters,
            )

        # ====================================================
        # SALES
        # ====================================================
        #
        # IMPORTANT:
        #
        # Dynamic sales requests include:
        #
        #   Show sales
        #   Show sales for the last 6 months
        #   Sales dashboard
        #   Compare revenue
        #   Show revenue by region
        #
        # These must all request sales resource data.
        # ====================================================

        if (
            "sales" in text
            or "revenue" in text
            or intent_name
            in {
                "sales",
                "sales_analysis",
                "sales_dashboard",
                "revenue",
                "revenue_analysis",
            }
        ):

            parameters: dict[str, Any] = {}

            # ------------------------------------------------
            # TIME RANGE
            # ------------------------------------------------

            if (
                "last 6 months" in text
                or "last six months" in text
            ):

                parameters["time_range"] = (
                    "last_6_months"
                )

            elif (
                "last 3 months" in text
                or "last three months" in text
            ):

                parameters["time_range"] = (
                    "last_3_months"
                )

            elif (
                "last 12 months" in text
                or "last twelve months" in text
            ):

                parameters["time_range"] = (
                    "last_12_months"
                )

            elif (
                "this month" in text
            ):

                parameters["time_range"] = (
                    "this_month"
                )

            elif (
                "last month" in text
            ):

                parameters["time_range"] = (
                    "last_month"
                )

            # ------------------------------------------------
            # REGION
            # ------------------------------------------------

            regions = [
                "north",
                "south",
                "east",
                "west",
            ]

            found_regions = [
                region
                for region in regions
                if region in text
            ]

            if found_regions:

                parameters["regions"] = (
                    found_regions
                )

            return ResourcePlan(
                requires_data=True,
                data_source="sales",
                operation="list",
                resource_type="sales",
                parameters=parameters,
            )

        # ====================================================
        # CUSTOMER
        # ====================================================

        if (
            "customer" in text
            or "customers" in text
            or "client" in text
            or "clients" in text
            or intent_name
            in {
                "customers",
                "customer_analysis",
                "customer_distribution",
            }
        ):

            parameters: dict[str, Any] = {}

            return ResourcePlan(
                requires_data=True,
                data_source="customers",
                operation="list",
                resource_type="customers",
                parameters=parameters,
            )

        # ====================================================
        # EMPLOYEE
        # ====================================================

        if (
            "employee" in text
            or "employees" in text
            or "staff" in text
            or intent_name
            in {
                "employees",
                "employee_information",
                "employee_management",
            }
        ):

            parameters: dict[str, Any] = {}

            return ResourcePlan(
                requires_data=True,
                data_source="employees",
                operation="list",
                resource_type="employees",
                parameters=parameters,
            )

        # ====================================================
        # STUDENT
        # ====================================================

        if (
            "student dashboard" in text
            or "student information" in text
            or intent_name
            in {
                "student_dashboard",
                "students",
            }
        ):

            return ResourcePlan(
                requires_data=True,
                data_source="student",
                operation="get",
                resource_type="student",
                parameters={},
            )

        # ====================================================
        # WEATHER
        # ====================================================

        if (
            "weather" in text
            or intent_name == "weather"
        ):

            location = (
                self._extract_location(
                    user_prompt
                )
            )

            return ResourcePlan(
                requires_data=True,
                data_source="weather_api",
                operation="current",
                resource_type="weather",
                parameters={
                    "location": location
                },
            )

        # ====================================================
        # NO RESOURCE REQUIRED
        # ====================================================

        return ResourcePlan(
            requires_data=False,
            data_source=None,
            operation=None,
            resource_type=None,
            parameters={},
        )

    # ========================================================
    # GET INTENT NAME
    # ========================================================

    @staticmethod
    def _get_intent(
        intent: Any,
    ) -> str:

        if intent is None:

            return ""

        if isinstance(
            intent,
            dict,
        ):

            value = intent.get(
                "intent",
                "",
            )

        else:

            value = getattr(
                intent,
                "intent",
                "",
            )

        return (
            str(value or "")
            .strip()
            .lower()
        )

    # ========================================================
    # INTENT CHECK
    # ========================================================

    @staticmethod
    def _intent_is(
        intent: Any,
        expected: str,
    ) -> bool:

        value = ResourcePlanner._get_intent(
            intent
        )

        return (
            value
            == expected.strip().lower()
        )

    # ========================================================
    # LOCATION
    # ========================================================

    @staticmethod
    def _extract_location(
        prompt: str,
    ) -> str:

        text = (
            prompt or ""
        ).strip()

        lower = text.lower()

        markers = [
            " in ",
            " at ",
            " for ",
        ]

        for marker in markers:

            index = lower.find(
                marker
            )

            if index != -1:

                location = text[
                    index
                    + len(marker):
                ].strip()

                if location:

                    return location.rstrip(
                        "?.!"
                    )

        return "Trichy"