"""
Multi-API step definitions — Gherkin steps for calling REST APIs.

Steps defined here:

    Given I use the "<ApiName>" API in "<env>" environment
    And   I prepare "<templateName>" template for this API with:
              | _version | v1    |
              | fieldA   | valueA |
    And   I add request header "<key>" = "<value>"
    When  I POST "<path>"
    When  I PUT "<path>"
    When  I GET "<path>"
    When  I DELETE "<path>"
    Then  the response status should be <code>
    And   I capture response fields:
              | varName | jsonPath |
"""

from behave import given, when, then, step

from pytaf.utils.api.api_registry import ApiRegistry
from pytaf.utils.api.auth_provider import from_cfg
from pytaf.utils.api.multi_api_client import MultiApiClient
from pytaf.utils.api import template_loader, conditional_templater, evidence_writer
from pytaf.utils.api.json_path_extractor import extract


# ------------------------------------------------------------------
# Context helpers
# ------------------------------------------------------------------

def _ctx(context) -> dict:
    """Per-scenario API state dict attached to the Behave context."""
    if not hasattr(context, "api_ctx"):
        context.api_ctx = {}
    return context.api_ctx


def _vars(context) -> dict:
    """Shared variable bag that persists across API calls within a scenario."""
    ctx = _ctx(context)
    return ctx.setdefault("vars", {})


# ------------------------------------------------------------------
# Step definitions
# ------------------------------------------------------------------

@given('I use the "{api_name}" API in "{env}" environment')
def step_use_api(context, api_name, env):
    cfg = ApiRegistry.get(env, api_name)
    auth = from_cfg(cfg)
    client = MultiApiClient(cfg.base_url, auth, cfg.default_headers)
    ctx = _ctx(context)
    ctx["apiClient"] = client
    ctx["apiName"] = api_name
    ctx["apiEnv"] = env
    ctx["lastHeaders"] = {}


@given('I prepare "{template_name}" template for this API with')
def step_prepare_template(context, template_name):
    data: dict[str, str] = {row[0]: row[1] for row in context.table}
    ctx = _ctx(context)
    api_name = ctx["apiName"]
    version = data.pop("_version", "v1")

    path = f"src/test/resources/api/{api_name}/{version}/templates/{template_name}.json"
    raw = template_loader.load(path)

    all_vars: dict = {**_vars(context), **data}
    with_conds = conditional_templater.render(raw, all_vars)
    filled = template_loader.render(with_conds, all_vars, validate_json=True)

    ctx["lastPayload"] = filled
    ctx["lastHeaders"] = {}


@step('I add request header "{key}" = "{value}"')
def step_add_header(context, key, value):
    _ctx(context)["lastHeaders"][key] = value


@when('I POST "{path}"')
def step_post(context, path):
    _send_with_body(context, "POST", path)


@when('I PUT "{path}"')
def step_put(context, path):
    _send_with_body(context, "PUT", path)


@when('I GET "{path}"')
def step_get(context, path):
    ctx = _ctx(context)
    client: MultiApiClient = ctx["apiClient"]
    headers = ctx.get("lastHeaders", {})
    scenario_name = getattr(context.scenario, "name", "Scenario")
    evidence_dir = evidence_writer.save_request(scenario_name, "GET", path, "", headers)
    resp = client.get(path, headers=headers)
    _cache(ctx, resp)
    evidence_writer.save_response(evidence_dir, resp)


@when('I DELETE "{path}"')
def step_delete(context, path):
    ctx = _ctx(context)
    client: MultiApiClient = ctx["apiClient"]
    headers = ctx.get("lastHeaders", {})
    scenario_name = getattr(context.scenario, "name", "Scenario")
    evidence_dir = evidence_writer.save_request(scenario_name, "DELETE", path, "", headers)
    resp = client.delete(path, headers=headers)
    _cache(ctx, resp)
    evidence_writer.save_response(evidence_dir, resp)


@then("the response status should be {code:d}")
def step_status(context, code):
    ctx = _ctx(context)
    actual = ctx.get("lastStatus")
    body = ctx.get("lastBody", "")
    assert actual == code, (
        f"Expected HTTP {code} but got {actual}.\nBody: {body}"
    )


@step("I capture response fields")
def step_capture_fields(context):
    ctx = _ctx(context)
    resp = ctx.get("lastResponse")
    assert resp is not None, "No API response found — did you call a request step first?"
    shared_vars = _vars(context)
    for row in context.table:
        var_name, json_expr = row[0], row[1]
        val = extract(resp, json_expr)
        if val is not None:
            shared_vars[var_name] = val


# ------------------------------------------------------------------
# Internal
# ------------------------------------------------------------------

def _send_with_body(context, method: str, path: str) -> None:
    ctx = _ctx(context)
    client: MultiApiClient = ctx["apiClient"]
    body: str = ctx.get("lastPayload", "")
    headers: dict = ctx.get("lastHeaders", {})
    scenario_name = getattr(context.scenario, "name", "Scenario")
    evidence_dir = evidence_writer.save_request(scenario_name, method, path, body, headers)
    resp = client.post_json(path, body, headers) if method == "POST" else client.put_json(path, body, headers)
    _cache(ctx, resp)
    evidence_writer.save_response(evidence_dir, resp)


def _cache(ctx: dict, resp) -> None:
    ctx["lastResponse"] = resp
    ctx["lastStatus"] = resp.status_code
    ctx["lastBody"] = resp.as_string()
