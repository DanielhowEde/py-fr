@regression
Feature: User Management — Create users with assigned roles

  Background:
    Given I use the "Users" API in "dev" environment

  # ── Single test: create one user ──────────────────────────────────────────

  Scenario: Create a single user via API
    Given I prepare "create-user" template for this API with:
      | _version     | v1                       |
      | email        | jane.doe@coreportal.app  |
      | display_name | Jane Doe                 |
      | role_id      | ab8a44e7-bbf1-4b1e-88c4-e0c5bc00404f |
    When I POST "/admin/users"
    Then the response status should be 201
    And I capture response fields:
      | userId | $.id    |
      | email  | $.email |

  # ── Spreadsheet-driven: create multiple users from Excel ──────────────────

  @test_create_users
  Scenario: Create users from spreadsheet data
    Given I load spreadsheet data for this test
    And I load iteration 1 from the spreadsheet
    And I prepare "create-user" template for this API with:
      | _version     | v1              |
      | email        | {email}         |
      | display_name | {display_name}  |
      | role_id      | {role_id}       |
    When I POST "/admin/users"
    Then the response status should be 201
    And I capture response fields:
      | userId | $.id |

  @test_create_users
  Scenario: Create batch of users from spreadsheet — all iterations
    Given I load spreadsheet data for this test
    And I create all users from the spreadsheet

  # ── Verify users exist ────────────────────────────────────────────────────

  Scenario: List all users
    When I GET "/admin/users"
    Then the response status should be 200
    And I capture response fields:
      | totalUsers | $.total |

  # ── Spreadsheet-driven: full file ─────────────────────────────────────────

  @testfile_create_users
  Scenario: Run all user tests from spreadsheet
    Given I load all tests from the spreadsheet
    And I execute each test from the spreadsheet
