"""Dummy tools for HR automation."""
from typing import Dict


def create_hr_ticket(issue: str) -> Dict[str, str]:
    """
    Create an HR ticket for the given issue.

    Args:
        issue: Description of the HR issue

    Returns:
        Dict with ticket information
    """
    return {
        "ticket_id": "TICKET-1234",
        "status": "created",
        "issue": issue,
        "message": f"HR ticket created successfully. Ticket ID: TICKET-1234"
    }


def check_leave_balance(employee_id: str) -> Dict[str, str]:
    """
    Check leave balance for an employee.

    Args:
        employee_id: Employee ID

    Returns:
        Dict with leave balance information
    """
    return {
        "employee_id": employee_id,
        "leave_balance": 8,
        "message": f"Employee {employee_id} has 8 leave days remaining."
    }


# Tool registry for easy access
TOOLS = {
    "create_hr_ticket": create_hr_ticket,
    "check_leave_balance": check_leave_balance
}

