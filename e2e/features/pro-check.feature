Feature: Pro Subscription Check — plan-based routing

  Scenario: Pro user skips usage check and action proceeds
    Given a pro user is authenticated
    When the user submits text to any AI action
    Then the action completes without a 429 response

  Scenario: Plan lookup failure defaults to free tier behaviour
    Given the database is unavailable for plan lookup
    When the user submits text to brainstorm
    Then the action either completes or returns a structured error
