Feature: Brainstorm — synchronous text operation

  Scenario: User submits text and receives brainstorm result
    When the user submits text to brainstorm
    Then "[data-test='brainstorm-result']" is visible within 60 seconds

  Scenario: Skill failure shows polling error
    Given the backend returns a 500 error for brainstorm
    When the user submits text to brainstorm
    Then "[data-test='polling-error']" is visible
