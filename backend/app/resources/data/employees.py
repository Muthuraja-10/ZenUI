from __future__ import annotations

from typing import Any


# ============================================================
# EMPLOYEE DATA
# ============================================================

EMPLOYEES: list[dict[str, Any]] = [
    {
        "employee_id": "EMP-001",
        "name": "Arun Kumar",
        "department": "Engineering",
        "role": "Software Engineer",
        "location": "Chennai",
        "status": "Active",
    },
    {
        "employee_id": "EMP-002",
        "name": "Priya Sharma",
        "department": "Human Resources",
        "role": "HR Manager",
        "location": "Chennai",
        "status": "Active",
    },
    {
        "employee_id": "EMP-003",
        "name": "Rahul Singh",
        "department": "Finance",
        "role": "Financial Analyst",
        "location": "Bangalore",
        "status": "Active",
    },
    {
        "employee_id": "EMP-004",
        "name": "Divya Raj",
        "department": "Engineering",
        "role": "Frontend Developer",
        "location": "Trichy",
        "status": "Active",
    },
    {
        "employee_id": "EMP-005",
        "name": "Karthik S",
        "department": "Operations",
        "role": "Operations Executive",
        "location": "Chennai",
        "status": "Inactive",
    },
]


# ============================================================
# GET EMPLOYEES
# ============================================================

def get_employees(
    department: str | None = None,
) -> list[dict[str, Any]]:

    if not department:
        return EMPLOYEES.copy()

    normalized_department = (
        department.strip().lower()
    )

    return [
        employee
        for employee in EMPLOYEES
        if str(
            employee.get("department", "")
        ).lower()
        == normalized_department
    ]