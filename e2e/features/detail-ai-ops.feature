Feature: Project Detail — AI Text Operation Chips (PD-08, PD-09)

  @detail @PD-08 @SKIP_MOCK @smoke
  Scenario: AI operation chips are visible when a spec file is open
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    When the user clicks the "analysis" sidebar file
    Then the AI operation chips are visible in the sidebar
    And the AI operation chips panel contains multiple chips

  @detail @PD-08 @SKIP_MOCK
  Scenario: An AI op chip can be toggled to the active state
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    When the user clicks the "analysis" sidebar file
    And the user toggles the "Expand" AI op chip
    Then the "Expand" AI op chip is active

  @detail @PD-09 @SKIP_MOCK @smoke
  Scenario: Style preset chips render when the Style op is selected
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    When the user clicks the "analysis" sidebar file
    And the user toggles the "Style" AI op chip
    Then the style preset chips are visible
    And the style preset chips panel contains multiple presets

  @detail @PD-09 @SKIP_MOCK
  Scenario: A style preset chip can be selected to trigger a style rewrite
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    When the user clicks the "analysis" sidebar file
    And the user toggles the "Style" AI op chip
    Then the style preset chips are visible
    When the user selects the "Formal" style preset
    Then the Generate Specs button enters a loading state
