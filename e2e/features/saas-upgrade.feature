Feature: SaaS Upgrade Page (SA-12, SA-20, SA-21)

  @saas @SA-12 @smoke
  Scenario: The upgrade page renders the free plan call-to-action for a free-plan user
    Given the user is logged in as a free-plan user
    When the user navigates to the upgrade page
    Then the page shell is not visible
    And the upgrade page shows the free plan call-to-action

  @saas @SA-20 @SKIP_MOCK
  Scenario: A lapsed plan shows a different call-to-action than a free plan
    Given a 429 rate-limit response is configured
    When the user navigates to the upgrade page
    Then the upgrade page shows the lapsed plan call-to-action

  @saas @SA-21 @SKIP_MOCK
  Scenario: The checkout button triggers a redirect to the Stripe checkout URL
    Given the user is logged in as a free-plan user
    When the user navigates to the upgrade page
    Then clicking the checkout button triggers a Stripe redirect
