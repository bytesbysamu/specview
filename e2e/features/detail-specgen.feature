Feature: Project Detail — Spec Generation Pipeline (PD-01, PD-06, PD-07)

  @detail @PD-01 @SKIP_MOCK @smoke
  Scenario: Full spec-gen pipeline runs and completes with incremental file saves
    Given the user is logged in and a braindump-only project exists
    And the user is on the detail view of that project
    And a spec-generation pipeline is in progress for that project
    When the user clicks the Generate Specs button
    Then the Generate Specs button enters a loading state
    And the sidebar status row transitions to active mode
    And each generated file shows a dot indicator during generation
    And the spec generation pipeline completes successfully
    And the sidebar file list is updated with generated files

  @detail @PD-06 @SKIP_MOCK
  Scenario: Clicking Generate Specs triggers the pipeline and shows loading state
    Given the user is logged in and a braindump-only project exists
    And the user is on the detail view of that project
    When the user clicks the Generate Specs button
    Then the Generate Specs button enters a loading state
    And the sidebar status row transitions to active mode

  @detail @PD-07 @SKIP_MOCK
  Scenario: Clicking Generate Guide triggers guide generation and shows loading state
    Given the user is logged in and a full-spec project exists
    And the user is on the detail view of that project
    When the user clicks the Generate Guide button
    Then the Generate Guide button enters a loading state
