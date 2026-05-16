Feature: Project Detail — Brainstorm Follow-Up and Spec Generation (PD-13, PD-14)

  @detail @PD-13 @SKIP_MOCK @smoke
  Scenario: Brainstorm follow-up input is visible after a brainstorm result
    Given the user is logged in and a braindump-only project exists
    And the user is on the detail view of that project
    And an AI operation result is available in the result panel
    Then the brainstorm follow-up input is visible

  @detail @PD-13 @SKIP_MOCK
  Scenario: User can type a follow-up question and submit it
    Given the user is logged in and a braindump-only project exists
    And the user is on the detail view of that project
    And an AI operation result is available in the result panel
    When the user types "What are the biggest risks?" in the brainstorm follow-up input
    And the user submits the brainstorm follow-up
    Then the brainstorm result panel updates with the follow-up answer

  @detail @PD-14 @SKIP_MOCK @smoke
  Scenario: Generate Specs button is visible after a brainstorm result on a braindump
    Given the user is logged in and a braindump-only project exists
    And the user is on the detail view of that project
    And an AI operation result is available in the result panel
    Then the Generate Specs from brainstorm button is visible

  @detail @PD-14 @SKIP_MOCK
  Scenario: Clicking Generate Specs from brainstorm triggers the spec pipeline
    Given the user is logged in and a braindump-only project exists
    And the user is on the detail view of that project
    And an AI operation result is available in the result panel
    When the user clicks Generate Specs from the brainstorm result
    Then the sidebar status row transitions to active mode
