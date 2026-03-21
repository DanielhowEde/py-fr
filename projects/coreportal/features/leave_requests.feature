@regression @leave
Feature: Leave Requests — Employee submits, Manager approves

  As an employee I can submit a leave request.
  As a manager I can approve or reject leave requests from my team.

  Background:
    Given I use the "Leave" API in "dev" environment

  # ── Employee: Submit Leave ───────────────────────────────────────────────

  Scenario: Employee checks their leave balance
    When I GET "/leave/my/balance"
    Then the response status should be 200

  Scenario: Employee checks their entitlement
    When I GET "/leave/my/entitlement"
    Then the response status should be 200

  Scenario: Employee creates a leave request
    Given I prepare "create-leave-request" template for this API with:
      | _version   | v1                 |
      | leave_type | annual             |
      | start_date | 2026-04-14         |
      | end_date   | 2026-04-18         |
      | reason     | Family holiday     |
    When I POST "/leave/my/requests"
    Then the response status should be 201
    And I capture response fields:
      | leaveRequestId | $.id     |
      | leaveStatus    | $.status |

  Scenario: Employee submits the leave request for approval
    # Requires leaveRequestId from the previous scenario
    When I POST "/leave/my/requests/{leaveRequestId}/submit"
    Then the response status should be 200

  Scenario: Employee views their leave requests
    When I GET "/leave/my/requests"
    Then the response status should be 200

  # ── Manager: Approve / Reject ────────────────────────────────────────────

  Scenario: Manager views team leave requests
    When I GET "/leave/team/requests"
    Then the response status should be 200

  Scenario: Manager views team calendar
    When I GET "/leave/team/calendar"
    Then the response status should be 200

  Scenario: Manager approves a pending leave request
    # Requires leaveRequestId from earlier in the flow
    When I POST "/leave/team/requests/{leaveRequestId}/approve"
    Then the response status should be 200

  Scenario: Manager rejects a leave request with reason
    Given I add request header "Content-Type" = "application/json"
    When I POST "/leave/team/requests/{leaveRequestId}/reject"
    Then the response status should be 200

  # ── Employee: Cancel Leave ───────────────────────────────────────────────

  Scenario: Employee cancels a leave request
    When I POST "/leave/my/requests/{leaveRequestId}/cancel"
    Then the response status should be 200

  # ── Spreadsheet-driven: Bulk leave requests ──────────────────────────────

  @test_leave_requests
  Scenario: Submit leave requests from spreadsheet data
    Given I load spreadsheet data for this test
    And I submit all leave requests from the spreadsheet

  @test_leave_approvals
  Scenario: Manager approves leave requests from spreadsheet
    Given I load spreadsheet data for this test
    And I process all leave approvals from the spreadsheet
