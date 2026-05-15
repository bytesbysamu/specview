Feature: Overview — Create Project Modal (OV-13)

  @overview @OV-13 @smoke
  Scenario: Clicking the New button opens the create project modal
    Given the user is logged in and on the overview page
    When the user clicks the New Project button
    Then the create project modal is visible
    And the project name input is focused

  @overview @OV-13
  Scenario: Submitting valid inputs closes the modal and starts generation
    Given the user is logged in and the create project modal is open
    And the user has entered a project name and a braindump
    When the user clicks the Generate button
    Then the modal closes immediately
    And the generation status bar transitions to the active state

  @overview @OV-13
  Scenario: Clicking the modal backdrop closes the modal without starting generation
    Given the user is logged in and the create project modal is open
    When the user clicks outside the modal dialog
    Then the modal closes without starting generation

  @overview @OV-13
  Scenario: The Generate button is disabled while generation is already in progress
    Given the user is logged in and the create project modal is open
    And spec generation is already in progress
    Then the Generate button is disabled

  @overview @OV-13
  Scenario: Any previous generation error is cleared when the modal is opened
    Given a previous spec generation ended with an error
    When the user opens the create project modal
    Then no error message is shown inside the modal
