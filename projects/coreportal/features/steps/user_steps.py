"""
Step definitions for Core Portal user management.

These steps extend the built-in pytaf API steps with user-creation logic
that reads from the spreadsheet data loaded by @test_ / @testfile_ tags.
"""

from behave import given, then
from pytaf.utils.api.multi_api_client import MultiApiClient


@given("I create all users from the spreadsheet")
def step_create_all_users(context):
    """Iterate every iteration in the loaded spreadsheet data and POST each user."""
    data = context.scenario_ctx.get("spreadsheet_data")
    assert data, "No spreadsheet data loaded — use 'I load spreadsheet data for this test' first"

    client: MultiApiClient = context.scenario_ctx.get("_api_client")
    assert client, "No API client — use 'I use the ... API in ... environment' first"

    created = []
    for iteration, rows in sorted(data.items()):
        for row in rows:
            body = {
                "email": row["email"],
                "display_name": row["display_name"],
                "role_id": row["role_id"],
            }
            resp = client.post("/admin/users", json=body)
            status = resp.status_code
            assert status == 201, (
                f"Failed to create user {row['email']}: HTTP {status} — {resp.text}"
            )
            result = resp.json()
            created.append({
                "id": result.get("id"),
                "email": row["email"],
                "role": row.get("role_name", ""),
                "iteration": iteration,
            })

    context.scenario_ctx.set("created_users", created)
    context.scenario_ctx.set("created_user_count", len(created))


@then('I should have created {count:d} users')
def step_verify_user_count(context, count):
    actual = context.scenario_ctx.get("created_user_count") or 0
    assert actual == count, f"Expected {count} users created, got {actual}"
