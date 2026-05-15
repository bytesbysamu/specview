Feature: Overview — Search and Filter Bar (OV-07)

  @overview @OV-07 @smoke
  Scenario: The search bar is visible when a named section is active and the grid is shown
    Given the user is logged in and on the overview page
    And the "All" section is active
    And the expanded panel is closed
    Then the search input is visible

  @overview @OV-07
  Scenario: The search bar is hidden when the Context section is active
    Given the user is logged in and on the overview page
    When the user clicks the "Context" section tab
    Then the search input is not visible

  @overview @OV-07
  Scenario: Typing in the search bar filters the project grid and shows a match count
    Given the user is logged in and on the overview page
    And 5 projects exist, 2 of which have "alpha" in their name
    When the user types "alpha" into the search input
    Then the project grid shows 2 results
    And the search bar displays "2 matches"

  @overview @OV-07
  Scenario: Clearing the search query shows the total project count
    Given the user is logged in and on the overview page
    And 5 projects exist in the current section
    And the search input is currently empty
    Then the search bar displays "5 projects"

  @overview @OV-07
  Scenario: Search filtering is case-insensitive
    Given the user is logged in and on the overview page
    And a project named "Alpha Project" exists
    When the user types "ALPHA" into the search input
    Then the project grid includes the "Alpha Project" card
