"""
Login & Navigation step definitions — common Gherkin steps for any test module.

Uses context.page (Vibium Page) set by features/environment.py before_scenario.
"""

from behave import given, when, then

from pytaf.common.pages.login_pom import LoginPOM
from pytaf.common.pages.navigation_pom import NavigationPOM


def _login_page(context) -> LoginPOM:
    if not hasattr(context, "login_page"):
        context.login_page = LoginPOM(context.page)
    return context.login_page


def _nav_page(context) -> NavigationPOM:
    if not hasattr(context, "nav_page"):
        context.nav_page = NavigationPOM(context.page)
    return context.nav_page


@given('I open the URL "{url}"')
def step_open_url(context, url):
    context.page.go(url)


@given('I navigate to "{link}"')
def step_navigate_to(context, link):
    _nav_page(context).navigate_to(link)


@given('I login to site as "{alias}" user')
def step_login_to_site(context, alias):
    _login_page(context).login_to_site(alias)


@given('I login as "{alias}" user')
def step_login_as(context, alias):
    _login_page(context).login_as_user(alias)


@given('I enter "{text}" into the username field')
def step_enter_username(context, text):
    _login_page(context).enter_username(text)


@given('I enter "{text}" into the password field')
def step_enter_password(context, text):
    _login_page(context).enter_password(text)


@when("I click the login button")
def step_click_login(context):
    _login_page(context).click_login_button()


@then("the user logs out")
def step_logout(context):
    _login_page(context).log_out()


@then('I wait for "{seconds}" seconds')
def step_wait(context, seconds):
    _nav_page(context).wait_for(int(seconds))
