Feature: SaaS Billing UI (SA-08, SA-09, SA-10, SA-11)

  @saas @SA-08 @SKIP_MOCK
  Scenario: A 429 rate-limit response redirects the user to the upgrade page
    Given a 429 rate-limit response is configured
    When the user navigates to the overview page
    Then the user is redirected to the upgrade page

  @saas @SA-09 @smoke
  Scenario: The usage remaining count displays in the header for free-plan users
    Given the user is logged in as a free-plan user
    When the user navigates to the overview page
    Then the usage remaining count is displayed in the header

  @saas @SA-10 @SA-07 @smoke
  Scenario: The usage meter is visible for a free-plan user
    Given the user is logged in as a free-plan user
    When the user navigates to the overview page
    Then the usage meter is visible in the header

  @saas @SA-11 @smoke
  Scenario: The upgrade button appears in the masthead for non-pro users
    Given the user is logged in as a free-plan user
    When the user navigates to the overview page
    Then the upgrade button is visible in the masthead
