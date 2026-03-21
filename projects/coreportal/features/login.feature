@smoke
Feature: Core Portal Login

  Background:
    Given I open the URL "http://18.134.7.166/login"

  Scenario: Successful admin login
    Given I enter "admin@coreportal.app" into the username field
    And I enter "admin" into the password field
    When I click the login button
    Then I wait for "2" seconds

  Scenario: Login with invalid credentials shows error
    Given I enter "invalid@example.com" into the username field
    And I enter "wrongpassword" into the password field
    When I click the login button
    Then I wait for "2" seconds

  @credential_store
  Scenario: Login using credential store alias
    Given I login as "admin" user
    Then I wait for "2" seconds
