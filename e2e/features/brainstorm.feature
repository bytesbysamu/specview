Feature: Brainstorm — synchronous text operation

  Scenario: User submits text and receives brainstorm result
    Given the app is loaded at "http://localhost:4201"
    When the user enters text in "[data-test='braindump-input']"
    And the user clicks "[data-test='brainstorm-button']"
    Then "[data-test='brainstorm-result']" is visible within 60 seconds

  Scenario: Skill failure shows polling error
    Given the backend returns a 500 error for brainstorm
    When the user submits text to brainstorm
    Then "[data-test='polling-error']" is visible
