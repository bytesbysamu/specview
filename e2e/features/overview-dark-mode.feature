Feature: Overview — Dark Mode Toggle and Persistence (OV-12)

  @overview @OV-12 @smoke
  Scenario: The theme toggle button is visible in the masthead
    Given the user is logged in and on the overview page
    Then the theme toggle button is visible in the masthead

  @overview @OV-12 @smoke
  Scenario: Clicking the theme toggle switches the page to dark mode
    Given the user is logged in and on the overview page in light mode
    When the user clicks the theme toggle button
    Then the page switches to dark mode
    And the dark mode theme attribute is set on the document root

  @overview @OV-12
  Scenario: Clicking the theme toggle a second time switches back to light mode
    Given the user is logged in and on the overview page in dark mode
    When the user clicks the theme toggle button
    Then the page switches to light mode
    And the light mode theme attribute is set on the document root

  @overview @OV-12
  Scenario: Theme preference is persisted to local storage after toggling
    Given the user is logged in and on the overview page in light mode
    When the user clicks the theme toggle button
    Then the theme preference stored in local storage is "dark"

  @overview @OV-12
  Scenario: Default theme is light when no preference has been saved
    Given the user is logged in and no theme preference is stored
    When the user loads the overview page
    Then the page renders in light mode
