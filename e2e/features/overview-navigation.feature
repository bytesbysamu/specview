Feature: Overview — Section Tab Navigation (OV-03)

  @overview @OV-03 @smoke
  Scenario: The overview page renders seven section navigation buttons
    Given the user is logged in and on the overview page
    Then seven section buttons are visible in the navigation bar

  @overview @OV-03 @smoke
  Scenario: The "All" section is active by default on page load
    Given the user is logged in and on the overview page
    Then the "All" section button is marked as active
    And no other section button is marked as active

  @overview @OV-03 @smoke
  Scenario: Clicking a section tab makes it the active section
    Given the user is logged in and on the overview page
    When the user clicks the "Specced" section tab
    Then the "Specced" section button is marked as active
    And the "All" section button is no longer marked as active

  @overview @OV-03
  Scenario: Clicking a section tab clears the current search query
    Given the user is logged in and on the overview page with a search query active
    When the user clicks the "Active" section tab
    Then the search input is cleared

  @overview @OV-03
  Scenario: Each section button shows a count badge reflecting the number of projects in that section
    Given the user is logged in and 3 projects exist in the Specced section
    When the user views the overview page
    Then the "Specced" section button badge shows 3
