Feature: Example smoke test

  Scenario: Open the homepage
    Given I open the URL "http://localhost:8080"
    Then I wait for "2" seconds
