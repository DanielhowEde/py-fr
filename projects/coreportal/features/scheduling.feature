@regression @scheduling
Feature: Scheduling — Shift templates, rotas, and assignments

  As a manager I need to create shift templates, build weekly rotas,
  assign employees to shifts, and submit the rota for the team.

  Background:
    Given I use the "Scheduling" API in "dev" environment

  # ── Admin: Shift Templates ───────────────────────────────────────────────

  Scenario: Create a Morning shift template
    Given I prepare "create-shift-template" template for this API with:
      | _version        | v1              |
      | name            | Morning Shift   |
      | start_time      | 08:00           |
      | end_time        | 16:00           |
      | crosses_midnight| false           |
      | break_minutes   | 30              |
      | break_paid      | false           |
    When I POST "/scheduling/admin/shift-templates"
    Then the response status should be 201
    And I capture response fields:
      | morningShiftId | $.id |

  Scenario: Create an Afternoon shift template
    Given I prepare "create-shift-template" template for this API with:
      | _version        | v1               |
      | name            | Afternoon Shift  |
      | start_time      | 14:00            |
      | end_time        | 22:00            |
      | crosses_midnight| false            |
      | break_minutes   | 30               |
      | break_paid      | false            |
    When I POST "/scheduling/admin/shift-templates"
    Then the response status should be 201
    And I capture response fields:
      | afternoonShiftId | $.id |

  Scenario: Create a Night shift template
    Given I prepare "create-shift-template" template for this API with:
      | _version        | v1            |
      | name            | Night Shift   |
      | start_time      | 22:00         |
      | end_time        | 06:00         |
      | crosses_midnight| true          |
      | break_minutes   | 45            |
      | break_paid      | true          |
    When I POST "/scheduling/admin/shift-templates"
    Then the response status should be 201
    And I capture response fields:
      | nightShiftId | $.id |

  Scenario: List all shift templates
    When I GET "/scheduling/admin/shift-templates"
    Then the response status should be 200

  # ── Manager: Rota Management ─────────────────────────────────────────────

  Scenario: Create a weekly rota
    Given I prepare "create-rota" template for this API with:
      | _version   | v1                 |
      | name       | Week 13 - 2026     |
      | start_date | 2026-03-23         |
      | end_date   | 2026-03-29         |
    When I POST "/scheduling/team/rotas"
    Then the response status should be 201
    And I capture response fields:
      | rotaId | $.id |

  Scenario: View the created rota
    When I GET "/scheduling/team/rotas"
    Then the response status should be 200

  # ── Manager: Submit Rota ─────────────────────────────────────────────────

  @depends_on_rota
  Scenario: Submit rota for the team
    # Requires rotaId from a previous run or stored context
    When I POST "/scheduling/team/rotas/{rotaId}/submit"
    Then the response status should be 200

  # ── Employee: My Schedule ────────────────────────────────────────────────

  Scenario: Employee views their schedule
    When I GET "/scheduling/my/schedule"
    Then the response status should be 200

  Scenario: Employee views their availability
    When I GET "/scheduling/my/availability"
    Then the response status should be 200

  # ── Spreadsheet-driven: Bulk shift creation ──────────────────────────────

  @test_create_shifts
  Scenario: Create shift templates from spreadsheet
    Given I load spreadsheet data for this test
    And I create all shifts from the spreadsheet
