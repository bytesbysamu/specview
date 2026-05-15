Feature: Overview — Authentication Gate (OV-01)

  @overview @OV-01 @smoke
  Scenario: Unauthenticated user is redirected away from the overview page
    Given the user is not logged in
    When the user navigates to the overview page
    Then the app shell renders the router outlet only
    And the main page shell is not visible

  @overview @OV-01 @smoke
  Scenario: Authenticated user on a regular route sees the full page shell
    Given the user is logged in
    When the user navigates to the overview page
    Then the main page shell is visible
    And the router outlet is not rendered directly

  @overview @OV-01
  Scenario: Authenticated user on a full-page route sees router outlet only
    Given the user is logged in
    When the user navigates to the upgrade page
    Then the app renders the router outlet only
    And the main page shell is not visible

  @overview @OV-01
  Scenario: Token expiry during a session collapses the page shell immediately
    Given the user is logged in and viewing the overview page
    When the user's authentication token expires
    Then the main page shell is hidden immediately
    And the app renders the router outlet only
