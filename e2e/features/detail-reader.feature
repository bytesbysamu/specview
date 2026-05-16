Feature: Project Detail — Reader Panel (PD-02, PD-15, PD-16)

  @detail @PD-02 @smoke
  Scenario: Selecting a project opens the expanded reader panel
    Given the user is logged in and a full-spec project exists
    When the user clicks on the project card
    Then the expanded reader panel is visible

  @detail @PD-15 @smoke
  Scenario: Spec files appear in canonical order in the sidebar
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    Then the sidebar file list shows files in canonical order

  @detail @PD-16
  Scenario: Markdown content renders with formatting in the reader
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    When the user clicks the "analysis" sidebar file
    Then the reader content area renders formatted markdown

  @detail @PD-16
  Scenario: Script tags are stripped from rendered markdown content
    Given the user is logged in and a project with XSS content exists
    And the user is on the detail view of that project
    When the user clicks the "braindump" sidebar file
    Then the reader content contains no script tags
