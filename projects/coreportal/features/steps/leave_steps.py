"""
Step definitions for Core Portal leave requests — submit and approve flow.
"""

from behave import given, then
from pytaf.utils.api.multi_api_client import MultiApiClient


@given("I submit all leave requests from the spreadsheet")
def step_submit_all_leave(context):
    """Create and submit each leave request from the loaded spreadsheet data."""
    data = context.scenario_ctx.get("spreadsheet_data")
    assert data, "No spreadsheet data loaded"

    client: MultiApiClient = context.scenario_ctx.get("_api_client")
    assert client, "No API client configured"

    submitted = []
    for iteration, rows in sorted(data.items()):
        for row in rows:
            # 1. Create the request
            body = {
                "leave_type": row["leave_type"],
                "start_date": str(row["start_date"]),
                "end_date": str(row["end_date"]),
                "reason": row.get("reason", ""),
            }
            resp = client.post("/leave/my/requests", json=body)
            assert resp.status_code == 201, (
                f"Failed to create leave request: HTTP {resp.status_code} — {resp.text}"
            )
            request_id = resp.json()["id"]

            # 2. Submit for approval
            resp = client.post(f"/leave/my/requests/{request_id}/submit")
            assert resp.status_code == 200, (
                f"Failed to submit leave request {request_id}: "
                f"HTTP {resp.status_code} — {resp.text}"
            )

            submitted.append({
                "id": request_id,
                "leave_type": row["leave_type"],
                "start_date": str(row["start_date"]),
                "iteration": iteration,
            })

    context.scenario_ctx.set("submitted_leave_requests", submitted)
    context.scenario_ctx.set("submitted_leave_count", len(submitted))


@given("I process all leave approvals from the spreadsheet")
def step_process_leave_approvals(context):
    """Approve or reject leave requests based on the 'action' column."""
    data = context.scenario_ctx.get("spreadsheet_data")
    assert data, "No spreadsheet data loaded"

    client: MultiApiClient = context.scenario_ctx.get("_api_client")
    assert client, "No API client configured"

    # First, get all pending team requests
    resp = client.get("/leave/team/requests")
    assert resp.status_code == 200, (
        f"Failed to fetch team requests: HTTP {resp.status_code}"
    )
    team_requests = resp.json().get("items", [])

    processed = []
    for iteration, rows in sorted(data.items()):
        for row in rows:
            action = row.get("action", "approve").lower()
            start_date = str(row["start_date"])

            # Find matching pending request by start_date and leave_type
            matching = [
                r for r in team_requests
                if r.get("start_date", "").startswith(start_date)
                and r.get("status") in ("pending", "submitted")
            ]
            if not matching:
                continue

            request_id = matching[0]["id"]

            if action == "approve":
                resp = client.post(f"/leave/team/requests/{request_id}/approve")
            else:
                resp = client.post(
                    f"/leave/team/requests/{request_id}/reject",
                    json={"reason": f"Rejected by test — {row.get('reason', '')}"},
                )

            assert resp.status_code == 200, (
                f"Failed to {action} leave request {request_id}: "
                f"HTTP {resp.status_code} — {resp.text}"
            )

            processed.append({
                "id": request_id,
                "action": action,
                "start_date": start_date,
            })

    context.scenario_ctx.set("processed_leave_actions", processed)
    context.scenario_ctx.set("processed_leave_count", len(processed))


@then("I should have submitted {count:d} leave requests")
def step_verify_leave_submit_count(context, count):
    actual = context.scenario_ctx.get("submitted_leave_count") or 0
    assert actual == count, f"Expected {count} leave requests submitted, got {actual}"


@then("I should have processed {count:d} leave approvals")
def step_verify_leave_approval_count(context, count):
    actual = context.scenario_ctx.get("processed_leave_count") or 0
    assert actual == count, f"Expected {count} leave approvals processed, got {actual}"
