Feature: Overview — Masthead Banner and Update Notification (OV-02, OV-06)

  @overview @OV-02 @smoke
  Scenario: Authenticated user sees the full masthead on the overview page
    Given the user is logged in and on the overview page
    Then the masthead is visible
    And the masthead displays the edition label "Specview"
    And the masthead displays the title "Specview"
    And the masthead displays the tagline "All the Specs Fit to Read"
    And the masthead displays today's date in long format

  @overview @OV-02
  Scenario: Masthead is absent when the user is not logged in
    Given the user is not logged in
    When the user navigates to the overview page
    Then the masthead is not visible

  @overview @OV-06
  Scenario: An update banner appears when the background poll detects new projects
    Given the user is logged in and viewing the overview page with 2 known projects
    When the background poll returns a project list with 3 projects
    Then an update banner is visible showing "+1 new"

  @overview @OV-06
  Scenario: Dismissing the update banner hides it immediately
    Given the update banner is showing "+1 new"
    When the user clicks the dismiss button on the banner
    Then the update banner is no longer visible

  @overview @OV-06
  Scenario: No update banner appears when the project count decreases
    Given the user is logged in and viewing the overview page with 3 known projects
    When the background poll returns a project list with 2 projects
    Then no update banner is visible
