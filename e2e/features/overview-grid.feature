Feature: Overview — Project Grid and Card Rendering (OV-08, OV-09)

  @overview @OV-08 @smoke
  Scenario: The "All" view groups projects into taxonomy sections in canonical order
    Given the user is logged in and projects exist in the Active, Specced, and Braindumps sections
    When the user views the overview page with the "All" section active
    Then the project grid shows the Active group before the Specced group
    And the Specced group appears before the Braindumps group

  @overview @OV-08 @smoke
  Scenario: Each project card displays the project name, teaser, spec count, and section label
    Given the user is logged in and a project "My Spec" exists in the Specced section with 4 specs
    When the user views the overview page
    Then a project card for "My Spec" is visible
    And the card shows the spec count badge with value 4
    And the card shows the section label for Specced

  @overview @OV-08
  Scenario: Selecting a named section shows a column layout instead of grouped sections
    Given the user is logged in and 5 projects exist in the Braindumps section
    When the user clicks the "Braindumps" section tab
    Then the project grid uses a column layout
    And no taxonomy section group headers are shown

  @overview @OV-08
  Scenario: An empty section shows an empty state indicator
    Given the user is logged in and no projects exist in the Active section
    When the user clicks the "Active" section tab
    Then the empty state indicator is visible
    And no project cards are shown

  @overview @OV-09
  Scenario: An Active project card teaser shows the current generation step
    Given the user is logged in and a project "Live Build" is actively generating at step "epic"
    When the user views the overview page with the "Active" section active
    Then the card for "Live Build" shows the teaser "generating epic…"
