Feature: Project Detail — Sidebar Navigation (PD-03, PD-04, PD-05)

  @detail @PD-03 @smoke
  Scenario: Clicking a filename in the sidebar loads that file in the reader
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    When the user clicks the "analysis" sidebar file
    Then the reader panel displays the analysis file content

  @detail @PD-03
  Scenario: The active sidebar file entry is highlighted
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    When the user clicks the "epic" sidebar file
    Then the "epic" sidebar file entry is marked as active

  @detail @PD-04 @smoke
  Scenario: The sidebar status row shows the current connection state
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    And the sidebar status row is visible
    Then the sidebar status row displays a connection state

  @detail @PD-05 @SKIP_MOCK
  Scenario: Per-file dot indicators appear next to each file during generation
    Given the user is logged in and a braindump-only project exists
    And the user is on the detail view of that project
    And a spec-generation pipeline is in progress for that project
    When the user clicks the Generate Specs button
    Then each generated file shows a dot indicator during generation
