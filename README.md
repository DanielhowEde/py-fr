# pytaf — Python Test Automation Framework

BDD test automation framework for UI and API testing, built on [Behave](https://behave.readthedocs.io/), [Allure](https://allurereport.org/), and [Vibium](https://vibium.dev/).
Python port of the Java `jate-fr` framework — existing Gherkin steps work without changes.

---

## Requirements

- Python 3.11+
- [Allure CLI](https://allurereport.org/docs/install/) (for HTML reports)
- Chrome (default browser; Vibium manages the driver)

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Configuration

All runtime settings live in `config.properties` at the project root.

| Key | Default | Description |
|-----|---------|-------------|
| `base.url` | _(empty)_ | Base URL of the application under test |
| `headless` | `false` | Run browser headlessly |
| `timeout` | `10` | Element wait timeout in seconds |
| `vibium.connect.url` | _(empty)_ | Remote BiDi URL — leave blank to launch locally |
| `report.name` | `pytaf` | Prefix for the test-reports directory |
| `login.username.selector` | `[name='username'],[name='email']` | CSS/XPath locator for the username field |
| `login.password.selector` | `[name='password'],[type='password']` | CSS/XPath locator for the password field |
| `login.button.selector` | `[type='submit']` | CSS/XPath locator for the login button |
| `login.logout.selector` | `[data-testid='logout'],#logout,.logout` | CSS/XPath locator for the logout element |
| `api.relaxed.https` | `false` | Disable SSL verification for API calls |
| `credential.file` | `credentials.enc` | Path to the encrypted credential file |

Environment variables override any key — replace `.` with `_` and uppercase, e.g. `BASE_URL` overrides `base.url`.

---

## Running Tests

### Run all features

```bash
behave
```

### Run a specific feature file

```bash
behave features/my_feature.feature
```

### Run scenarios matching a tag

```bash
behave --tags=@smoke
behave --tags=@regression
```

### Run with console output (no Allure formatter)

```bash
behave --format=pretty
```

### Generate and view the Allure report

```bash
# 1. Run tests (results written to allure-results/)
behave

# 2. Serve the report in your browser
allure serve allure-results
```

---

## Project Structure

```
├── config.properties          # Runtime configuration
├── behave.ini                 # Behave settings and formatter config
├── requirements.txt
├── features/
│   ├── environment.py         # Browser lifecycle hooks (before/after scenario)
│   ├── steps/
│   │   └── __init__.py        # Imports pytaf shared steps automatically
│   └── *.feature              # Your Gherkin feature files
└── pytaf/                     # Framework library
    ├── core/
    │   ├── base_page.py       # UI helper methods (click, fill, wait, etc.)
    │   └── browser_manager.py # Singleton Vibium browser lifecycle
    ├── common/
    │   ├── pages/
    │   │   ├── login_pom.py       # Login page object
    │   │   └── navigation_pom.py  # Navigation helper
    │   └── steps/
    │       ├── login_navigation_steps.py  # Built-in UI step definitions
    │       └── multi_api_steps.py         # Built-in API step definitions
    └── utils/
        ├── api/
        │   ├── api_registry.py        # Loads apis.yaml
        │   ├── auth_provider.py       # Auth strategies (none, API key, OAuth2)
        │   ├── multi_api_client.py    # HTTP client
        │   ├── template_loader.py     # JSON template rendering
        │   ├── json_path_extractor.py # JSONPath extraction from responses
        │   └── evidence_writer.py     # Saves request/response artifacts to disk
        ├── config/
        │   └── config_reader.py       # Reads config.properties
        └── context/
            └── scenario_context.py    # Thread-safe per-scenario data store
```

---

## Writing UI Tests

### Feature file

```gherkin
Feature: User login

  Scenario: Successful login
    Given I open the URL "https://myapp.com/login"
    And I enter "admin" into the username field
    And I enter "secret" into the password field
    When I click the login button
    Then I wait for "2" seconds
```

### Built-in UI steps

| Step | Description |
|------|-------------|
| `Given I open the URL "{url}"` | Navigate to an absolute URL |
| `Given I navigate to "{link}"` | Navigate relative to `base.url` |
| `Given I login to site as "{alias}" user` | Full login flow using env-var credentials |
| `Given I login as "{alias}" user` | Alias for above |
| `Given I enter "{text}" into the username field` | Type into the username input |
| `Given I enter "{text}" into the password field` | Type into the password input |
| `When I click the login button` | Submit the login form |
| `Then the user logs out` | Click the logout element |
| `Then I wait for "{seconds}" seconds` | Pause execution |

### Login credentials

Credentials are resolved by `CredentialStore` in priority order:

1. **Encrypted file** — `credentials.enc` decrypted with `PYTAF_CREDENTIAL_KEY` _(recommended)_
2. **Environment variables** — `{ALIAS}_USERNAME` / `{ALIAS}_PASSWORD` _(fallback)_

See [Credential Store](#credential-store) for full setup details.

### Custom page objects

Extend `BasePage` for your own pages:

```python
# features/steps/my_page.py
from pytaf.core.base_page import BasePage

class MyPage(BasePage):
    SUBMIT_BTN = "#submit"

    def submit(self):
        self.click_element_by_locator(self.SUBMIT_BTN)
```

`BasePage` provides: `click_element_by_locator`, `enter_text_in_field`, `get_text_from_element`, `is_element_visible`, `wait_until_element_visible`, `select_dropdown_option_by_text`, `capture_screenshot`, and more.

---

## Writing API Tests

### 1. Define your APIs — `src/test/resources/api/apis.yaml`

```yaml
envs:
  dev:
    Payments:
      baseUrl: https://dev.payments.example.com
      auth:
        type: oauth2_client_credentials
        tokenUrl: https://auth.example.com/token
        clientId: ${PAY_CLIENT_ID}
        clientSecret: ${PAY_CLIENT_SECRET}
        scope: payments.write
      defaultHeaders:
        Accept: application/json

    Users:
      baseUrl: https://dev.users.example.com
      auth:
        type: api_key
        header: X-API-Key
        value: ${USERS_API_KEY}
```

Supported auth types: `none`, `api_key`, `oauth2_client_credentials`.
`${ENV_VAR}` placeholders are expanded from environment variables.

### 2. Create JSON templates — `src/test/resources/api/<ApiName>/<version>/templates/`

```json
{
  "amount": ${amount},
  "currency": "${currency:GBP}",
  "reference": "${reference}"
}
```

Placeholder syntax:

| Syntax | Behaviour |
|--------|-----------|
| `${var}` | Replaced with value from step table; error if missing |
| `${var:default}` | Uses `default` if `var` not provided |
| `${{var}}` | Raw insert (no JSON quoting); `null` if missing |

### 3. Write the feature

```gherkin
Feature: Payments API

  Scenario: Create a payment
    Given I use the "Payments" API in "dev" environment
    And I prepare "create-payment" template for this API with:
      | _version  | v1         |
      | amount    | 100        |
      | currency  | USD        |
      | reference | REF-001    |
    When I POST "/payments"
    Then the response status should be 201
    And I capture response fields:
      | paymentId | $.id |
```

### Built-in API steps

| Step | Description |
|------|-------------|
| `Given I use the "{api}" API in "{env}" environment` | Select API and environment from `apis.yaml` |
| `And I prepare "{template}" template for this API with` | Load and render a JSON template |
| `And I add request header "{key}" = "{value}"` | Add a custom request header |
| `When I POST "{path}"` | Send POST with the prepared body |
| `When I PUT "{path}"` | Send PUT with the prepared body |
| `When I GET "{path}"` | Send GET request |
| `When I DELETE "{path}"` | Send DELETE request |
| `Then the response status should be {code}` | Assert HTTP status code |
| `And I capture response fields` | Extract JSONPath values into variables |

### JSONPath extraction modifiers

```gherkin
And I capture response fields:
  | firstId  | $.items[0].id        |
  | lastId   | $.items[-1].id\|last  |
  | count    | $.items\|size         |
  | ids      | $.items[*].id\|join(,)|
```

---

## Sharing Data Between Steps

Use `context.scenario_ctx` to pass values between step definitions within a scenario:

```python
context.scenario_ctx.set("orderId", "ORD-123")
order_id = context.scenario_ctx.get("orderId")
```

---

## Excel Spreadsheet Data

pytaf supports data-driven tests via Excel files. Each file can hold data for many test cases; the tag on the scenario selects which rows to load, and an `iteration` column lets a single scenario consume multiple sets of data in one execution.

`openpyxl` is already installed via `requirements.txt`.

---

### Required spreadsheet structure

Every data file must have these two columns as the first two columns, followed by any test-specific columns:

| test | iteration | _your columns…_ |
|------|-----------|-----------------|

| Column | Required | Rules |
|--------|----------|-------|
| `test` | Yes | Identifies which test case owns the row. Rows with a blank `test` value are **ignored**. |
| `iteration` | Yes | Groups rows into numbered sets within a test. Blank values default to `1`. |

Rows are processed in **iteration order**, then by **row order** within each iteration.

#### Example file — `login.xlsx`

| test | iteration | username | password |
|------|-----------|----------|----------|
| login | 1 | user1 | pass1 |
| login | 2 | user2 | pass2 |
| login | 2 | user3 | pass3 |
| checkout | 1 | shopper | pass4 |

- `@test_login` → picks up the 3 `login` rows only; `checkout` rows are ignored.
- Iteration 1 → single row (one login).
- Iteration 2 → two rows (e.g. adding multiple users in the same scenario).

---

### Tag convention

Tags follow the format `@test_<testname>`, where `<testname>` matches the value in the `test` column exactly.

```gherkin
@test_login
Scenario: Login with spreadsheet data
  Given I load spreadsheet data for this test
  And I login as the user from iteration 1
  Then I should be on the dashboard
```

The framework strips the tag prefix in `before_scenario` and stores two values in `scenario_ctx`:

```
@test_login      →  spreadsheet_tag  = "login"
                     spreadsheet_mode = "test"

@testfile_login  →  spreadsheet_tag  = "login"
                     spreadsheet_mode = "all"
```

The file is resolved from `src/test/resources/data/<filename>.xlsx`. The filename is the part of the tag before any `.` — e.g. `@test_login.xlsx` resolves to `login.xlsx`, `@test_login` also resolves to `login.xlsx` by convention.

---

### Loading data in step definitions

```python
# features/steps/spreadsheet_steps.py
from collections import defaultdict
from pathlib import Path
import openpyxl
from behave import given

DATA_DIR = Path("src/test/resources/data")


def _load_test_data(filename: str, test_name: str) -> dict[int, list[dict]]:
    """
    Load rows for a specific test name from an xlsx file.
    Returns a dict keyed by iteration number, each value a list of row dicts.
    Rows with a blank 'test' value are skipped.
    Blank 'iteration' values default to 1.
    Result is sorted by iteration, then by original row order.
    """
    path = DATA_DIR / f"{filename}.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]

    iterations: dict[int, list[dict]] = defaultdict(list)
    for row in ws.iter_rows(min_row=2, values_only=True):
        data = dict(zip(headers, row))
        if not data.get("test"):          # skip blank test rows
            continue
        if data["test"] != test_name:     # skip other tests
            continue
        iteration = int(data.get("iteration") or 1)
        iterations[iteration].append(data)

    wb.close()
    return dict(sorted(iterations.items()))


def _load_all_test_data(filename: str) -> dict[str, dict[int, list[dict]]]:
    """
    Load every test from the file.
    Returns an ordered dict: { test_name: { iteration: [rows] } }
    Test names are ordered by first appearance in the sheet.
    """
    path = DATA_DIR / f"{filename}.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]

    all_data: dict[str, dict[int, list[dict]]] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        data = dict(zip(headers, row))
        test_name = data.get("test")
        if not test_name:
            continue
        iteration = int(data.get("iteration") or 1)
        all_data.setdefault(test_name, defaultdict(list))
        all_data[test_name][iteration].append(data)

    wb.close()
    return {name: dict(sorted(iters.items())) for name, iters in all_data.items()}


@given("I load spreadsheet data for this test")
def step_load_spreadsheet(context):
    tag      = context.scenario_ctx.get("spreadsheet_tag")  # e.g. "login"
    filename = tag.split(".")[0]                             # strip extension if present
    context.spreadsheet_data = _load_test_data(filename, tag)
    context.scenario_ctx.set("spreadsheet_data", context.spreadsheet_data)


@given("I load all tests from the spreadsheet")
def step_load_all_tests(context):
    tag      = context.scenario_ctx.get("spreadsheet_tag")  # e.g. "login" from @testfile_login
    filename = tag.split(".")[0]
    context.all_tests_data = _load_all_test_data(filename)
    context.scenario_ctx.set("all_tests_data", context.all_tests_data)


@given("I execute each test from the spreadsheet")
def step_execute_all_tests(context):
    all_data = context.scenario_ctx.get("all_tests_data") or {}
    for test_name, iterations in all_data.items():
        context.scenario_ctx.set("spreadsheet_data", iterations)
        context.scenario_ctx.set("current_test_name", test_name)
        rows = iterations.get(1, [])
        if rows:
            for key, value in rows[0].items():
                if key not in ("test", "iteration"):
                    context.scenario_ctx.set(key, value)
            context.scenario_ctx.set("current_iteration_rows", rows)


@given("I load iteration {iteration:d} from the spreadsheet")
def step_load_iteration(context, iteration):
    data = context.scenario_ctx.get("spreadsheet_data") or {}
    rows = data.get(iteration, [])
    assert rows, f"No spreadsheet rows found for iteration {iteration}"
    # Store each column value from the first row directly onto scenario_ctx
    for key, value in rows[0].items():
        if key not in ("test", "iteration"):
            context.scenario_ctx.set(key, value)
    # Store the full row list for multi-row iterations
    context.scenario_ctx.set("current_iteration_rows", rows)
```

---

### Accessing iteration data in steps

```python
# Single-row iteration — read individual values directly
username = context.scenario_ctx.get("username")
password = context.scenario_ctx.get("password")

# Multi-row iteration — iterate the full list
rows = context.scenario_ctx.get("current_iteration_rows")
for row in rows:
    # e.g. add each user from this iteration
    add_user(row["username"], row["password"])
```

---

### Full scenario example

```gherkin
@test_login
Scenario: Login flows from spreadsheet
  Given I load spreadsheet data for this test
  # --- iteration 1: single login ---
  And I load iteration 1 from the spreadsheet
  And I login as the spreadsheet user
  Then I should be on the dashboard
  # --- iteration 2: add multiple users ---
  And I load iteration 2 from the spreadsheet
  And I add all users from the current iteration
```

---

### File location convention

```
src/
└── test/
    └── resources/
        └── data/
            ├── login.xlsx
            ├── payments.xlsx
            └── users.xlsx
```

---

### Running modes

Two tags control how much of a spreadsheet file is executed.

| Tag | What runs |
|-----|-----------|
| `@test_<testname>` | Only rows where `test == <testname>` |
| `@testfile_<filename>` | All tests in the file, in order of first appearance |

#### Mode 1 — single test

Tag the scenario with `@test_<testname>`. The step `I load spreadsheet data for this test` filters to only that test's rows.

```gherkin
@test_login
Scenario: Login test
  Given I load spreadsheet data for this test
  And I load iteration 1 from the spreadsheet
  And I login as the spreadsheet user
  Then I should be on the dashboard
```

#### Mode 2 — all tests in a file

Tag the scenario with `@testfile_<filename>`. The step `I load all tests from the spreadsheet` returns every unique test name from the file in row order. Your steps then iterate through them.

```gherkin
@testfile_login
Scenario: Run all login tests
  Given I load all tests from the spreadsheet
  And I execute each test from the spreadsheet
```

All step definitions live in the same `spreadsheet_steps.py` file documented in the [Loading data in step definitions](#loading-data-in-step-definitions) section above. Within your "execute each test" logic you can access the current test name and all its iterations:

```python
test_name  = context.scenario_ctx.get("current_test_name")
iterations = context.scenario_ctx.get("spreadsheet_data")   # {1: [...], 2: [...]}
```

---

### Selecting what to run from the CLI

```bash
# Run a single named test from its spreadsheet
behave --tags=@test_login

# Run all tests from a specific file
behave --tags=@testfile_login

# Run multiple named tests
behave --tags="@test_login or @test_checkout"

# Run every spreadsheet-driven scenario in the suite
behave --tags="@test_ or @testfile_"

# Run everything (no tag filter)
behave
```

---

## Credential Store

Test credentials are managed by `pytaf.utils.credentials.credential_store.CredentialStore`. It tries an encrypted file first and falls back to environment variables, so existing env-var setups continue to work unchanged.

---

### How it works

```
PYTAF_CREDENTIAL_KEY (env var)
        │
        ▼
credentials.enc  ──decrypt──►  { "admin": {username, password}, ... }
        │                               │
        │                               ▼
        │                    CredentialStore.get("admin")
        │                               │
        └── not found / no key ────────►│
                                        ▼
                              {ALIAS}_USERNAME / {ALIAS}_PASSWORD
                              (environment variables)
```

---

### Setup — encrypted file (recommended)

**Step 1 — generate a key**

```bash
python scripts/manage_credentials.py generate-key
# prints: sz3Ld8... (a 44-char base64 Fernet key)
```

Store this key securely (CI secrets, a vault, or a local `.env` file). Never commit it.

**Step 2 — store the key in `.env`**

```bash
cp .env.example .env
# edit .env and paste your key
```

`.env` is loaded automatically at test startup and is excluded from git by `.gitignore`. The key persists across reboots without re-exporting it each session.

**Step 3 — add credentials**

```bash
python scripts/manage_credentials.py add --alias admin
# Username: alice
# Password: (hidden)

python scripts/manage_credentials.py add --alias qa-user
```

**Step 4 — verify**

```bash
python scripts/manage_credentials.py list
# Aliases in credentials.enc:
#   admin    (username: alice)
#   qa-user  (username: bob)
```

Add `credentials.enc` to `.gitignore`. The key must be exported in every shell / CI environment that runs the tests.

---

### Setup — environment variables (fallback)

If `PYTAF_CREDENTIAL_KEY` is not set, `CredentialStore` reads from environment variables. Hyphens and spaces in the alias are converted to underscores and uppercased:

```bash
# alias "admin"
export ADMIN_USERNAME=alice
export ADMIN_PASSWORD=s3cr3t

# alias "qa-user"
export QA_USER_USERNAME=bob
export QA_USER_PASSWORD=hunter2
```

---

### Credential file location

The default file is `credentials.enc` in the project root. Override with `config.properties`:

```properties
credential.file=config/credentials.enc
```

---

### Managing credentials

```bash
# Generate a new key
python scripts/manage_credentials.py generate-key

# Add or update an alias
python scripts/manage_credentials.py add --alias <alias> [--file credentials.enc]

# List all aliases (usernames shown, passwords never)
python scripts/manage_credentials.py list [--file credentials.enc]

# Remove an alias
python scripts/manage_credentials.py remove --alias <alias> [--file credentials.enc]
```

---

### Using credentials in custom steps

```python
from pytaf.utils.credentials.credential_store import CredentialStore

username, password = CredentialStore.get("admin")
```

---

## Evidence Files

After each API call, request and response artifacts are written to:

```
test-reports/<report.name>_<timestamp>/api/<scenario>/<timestamp>/
  request.json
  request.headers.txt
  request.curl.txt
  response.status.txt
  response.headers.txt
  response.json
```

Sensitive headers (`Authorization`, `X-API-Key`, etc.) are automatically redacted.

---

## Adding Custom Steps

Create a Python file in `features/steps/` — Behave picks it up automatically:

```python
# features/steps/my_steps.py
from behave import then
from pytaf.core.base_page import BasePage

@then('I should see "{text}"')
def step_see_text(context, text):
    page_text = context.page.content()
    assert text in page_text, f"'{text}' not found on page"
```
