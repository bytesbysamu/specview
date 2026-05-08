Feature: Billing Gate — free tier usage limit

  Scenario: Free tier user above limit sees upgrade prompt
    Given a free-tier user has reached their daily limit
    When the user submits text to brainstorm
    Then "[data-test='billing-gate-message']" is visible
    And no job is enqueued

  Scenario: Pro user above free limit still proceeds
    Given a pro user is authenticated
    When the user submits text to brainstorm
    Then "[data-test='brainstorm-result']" is visible within 60 seconds
