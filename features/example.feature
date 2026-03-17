Feature: Example smoke test

  Scenario: Home page loads
    Given I navigate to "/"
    Then I should see "Welcome"

  Scenario: Navigate to a full URL
    Given I go to "https://example.com"
    Then I should see "Example Domain"
    And I take a screenshot "screenshots/example.png"
