Feature: Bootstrap Pipeline — async spec generation

  Scenario: User triggers pipeline and sees files generated
    Given a project exists with a braindump
    When the user triggers the spec pipeline
    Then the sidebar shows generated spec files within 180 seconds

  Scenario: Pipeline failure shows polling error
    Given the backend returns an error during bootstrap polling
    When the user triggers the spec pipeline
    Then "[data-test='polling-error']" is visible
