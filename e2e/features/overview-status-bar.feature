Feature: Overview — Generation Status Bar (OV-04, OV-05)

  @overview @OV-05 @smoke
  Scenario: Status bar shows idle state when no generation is in progress
    Given the user is logged in and on the overview page
    And no spec generation is running
    Then the generation status bar displays the idle state
    And the status bar shows the text "specview · idle — ready"

  @overview @OV-05
  Scenario: Status bar shows active state with project name and step label during generation
    Given the user is logged in and on the overview page
    And spec generation is running for project "My Project" at step "analysis"
    Then the generation status bar displays the active state
    And the status bar shows the project name "My Project"
    And the status bar shows the step label "analysis"
    And a Cancel button is visible in the status bar

  @overview @OV-05
  Scenario: Status bar shows a success flash after generation completes
    Given the user is logged in and on the overview page
    And spec generation for project "My Project" has just completed successfully
    Then the generation status bar displays the success state
    And the status bar shows "My Project" and "done"

  @overview @OV-05
  Scenario: Status bar shows failure state with error message and a retry button
    Given the user is logged in and on the overview page
    And spec generation has failed with message "AI provider unavailable"
    Then the generation status bar displays the failure state
    And the status bar shows the error message "AI provider unavailable"
    And a retry button is visible in the status bar

  @overview @OV-04
  Scenario: A section count badge pulses briefly when its project count changes
    Given the user is logged in and on the overview page with projects loaded
    When a new project is added to the Active section
    Then the Active section count badge briefly shows a pulsing animation
