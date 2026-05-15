Feature: Overview — Background Polling Lifecycle (OV-10, OV-11)

  @overview @OV-10 @smoke
  Scenario: The project list refreshes automatically while the user is logged in
    Given the user is logged in and on the overview page
    And the initial project list has 2 projects
    When a background poll interval elapses
    And the server now returns 3 projects
    Then the project grid updates to show 3 projects

  @overview @OV-10
  Scenario: A polling error indicator appears after the retry threshold is reached
    Given the user is logged in and on the overview page
    And the test environment has POLL_MAX_RETRIES set to 2
    When the background poll fails 2 consecutive times
    Then the polling error indicator is visible
    And no further poll requests are made

  @overview @OV-10
  Scenario: Polling stops when the user logs out
    Given the user is logged in and background polling is active
    When the user logs out
    Then no further background poll requests are made

  @overview @OV-11
  Scenario: Dark mode preference saved as dark is restored on page load
    Given the user has previously set their theme preference to dark
    When the user loads the overview page
    Then the page renders in dark mode
    And the theme toggle button shows the light mode icon
