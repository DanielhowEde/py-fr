"""
Step definitions for Core Portal scheduling — shift templates, rotas, assignments.
"""

from behave import given, then
from pytaf.utils.api.multi_api_client import MultiApiClient


@given("I create all shifts from the spreadsheet")
def step_create_all_shifts(context):
    """POST each shift template from the loaded spreadsheet data."""
    data = context.scenario_ctx.get("spreadsheet_data")
    assert data, "No spreadsheet data loaded"

    client: MultiApiClient = context.scenario_ctx.get("_api_client")
    assert client, "No API client configured"

    created = []
    for iteration, rows in sorted(data.items()):
        for row in rows:
            body = {
                "name": row["name"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "crosses_midnight": bool(row.get("crosses_midnight", False)),
                "break_duration_minutes": int(row.get("break_minutes", 0)),
                "break_is_paid": bool(row.get("break_paid", False)),
                "colour_key": "shift-default",
                "is_active": True,
            }
            resp = client.post("/scheduling/admin/shift-templates", json=body)
            assert resp.status_code == 201, (
                f"Failed to create shift '{row['name']}': "
                f"HTTP {resp.status_code} — {resp.text}"
            )
            result = resp.json()
            created.append({"id": result["id"], "name": row["name"]})

    context.scenario_ctx.set("created_shifts", created)
    context.scenario_ctx.set("created_shift_count", len(created))


@then("I should have created {count:d} shifts")
def step_verify_shift_count(context, count):
    actual = context.scenario_ctx.get("created_shift_count") or 0
    assert actual == count, f"Expected {count} shifts, got {actual}"
