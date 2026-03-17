"""
Common Gherkin step definitions backed by Vibium browser automation.
"""

from behave import given, when, then


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

@given('I navigate to "{path}"')
def step_navigate(context, path):
    url = path if path.startswith("http") else context.base_url.rstrip("/") + "/" + path.lstrip("/")
    context.page.go(url)


@given('I go to "{url}"')
def step_go(context, url):
    context.page.go(url)


# ---------------------------------------------------------------------------
# Interaction
# ---------------------------------------------------------------------------

@when('I click "{selector}"')
def step_click(context, selector):
    context.page.find(selector).click()


@when('I type "{text}" into "{selector}"')
def step_type(context, text, selector):
    element = context.page.find(selector)
    element.click()
    element.type(text)


@when('I clear and type "{text}" into "{selector}"')
def step_clear_type(context, text, selector):
    element = context.page.find(selector)
    element.click()
    element.clear()
    element.type(text)


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

@then('I should see "{text}"')
def step_see_text(context, text):
    page_text = context.page.text()
    assert text in page_text, f"Expected to find '{text}' on page, but got:\n{page_text[:500]}"


@then('I should not see "{text}"')
def step_not_see_text(context, text):
    page_text = context.page.text()
    assert text not in page_text, f"Expected NOT to find '{text}' on page"


@then('the element "{selector}" should exist')
def step_element_exists(context, selector):
    element = context.page.find(selector)
    assert element is not None, f"Element '{selector}' not found on page"


@then('I take a screenshot "{filename}"')
def step_screenshot(context, filename):
    png = context.page.screenshot()
    with open(filename, "wb") as f:
        f.write(png)
