Feature: Project Detail — AI Result Panel and Toolbar (PD-10, PD-11, PD-12)

  @detail @PD-10 @SKIP_MOCK @smoke
  Scenario: AI result panel displays a diff view after an operation completes
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    And an AI operation result is available in the result panel
    Then the result panel shows a diff view
    And the floating result toolbar is visible

  @detail @PD-11 @SKIP_MOCK @smoke
  Scenario: Apply button applies the AI result to the file content
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    And an AI operation result is available in the result panel
    When the user clicks the Apply button in the result toolbar
    Then the reader content is updated with the applied result
    And the result toolbar disappears

  @detail @PD-11 @SKIP_MOCK
  Scenario: Dismiss button removes the AI result without applying it
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    And an AI operation result is available in the result panel
    When the user clicks the Dismiss button in the result toolbar
    Then the result toolbar disappears

  @detail @PD-11 @SKIP_MOCK
  Scenario: Copy button is available in the result toolbar
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    And an AI operation result is available in the result panel
    Then the floating result toolbar is visible
    When the user clicks the Copy button in the result toolbar
    Then the floating result toolbar is visible

  @detail @PD-12 @SKIP_MOCK @smoke
  Scenario: Undo button appears after applying an AI result
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    And an AI operation result is available in the result panel
    When the user clicks the Apply button in the result toolbar
    Then the undo button is visible in the sidebar

  @detail @PD-12 @SKIP_MOCK
  Scenario: Undo reverts applied change and redo becomes available
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    And the undo stack has at least one applied change
    When the user clicks the Undo button
    Then the redo button becomes visible in the sidebar
    And the reader content reverts to its previous state
