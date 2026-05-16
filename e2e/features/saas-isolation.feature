Feature: SaaS Project Isolation (SA-06)

  @saas @SA-06 @smoke
  Scenario: User B navigating to user A's project receives a 403 access-denied response
    Given user A is registered and has a project
    And user B is logged in
    When user B navigates to user A's project
    Then the access-denied panel is visible

  @saas @SA-06
  Scenario: The 403 page displays an ownership error message
    Given user A is registered and has a project
    And user B is logged in
    When user B navigates to user A's project
    Then the access-denied message contains ownership text

  @saas @SA-06
  Scenario: The back button on the 403 page navigates the user away from the denied project
    Given user A is registered and has a project
    And user B is logged in
    When user B navigates to user A's project
    And the user clicks the back button on the access-denied panel
    Then the access-denied panel is no longer visible
