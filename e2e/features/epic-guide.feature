Feature: Epic Guide Generation — async guide generation

  Scenario: User generates epic guide and it appears
    Given a project with an epic file exists
    When the user clicks "[data-test='epic-guide-trigger']"
    Then the guide file appears within 90 seconds

  Scenario: Guide generation timeout shows polling error
    Given the backend polling times out
    When the user triggers epic guide generation
    Then "[data-test='polling-error']" is visible after 60 seconds of retries
