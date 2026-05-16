Feature: SaaS Authentication (SA-01, SA-02, SA-04, SA-13)

  @saas @SA-01 @SA-03 @smoke
  Scenario: User logs in with valid credentials and lands on the overview page
    Given the user is not logged in and is on the login page
    When the user submits the login form with valid credentials
    Then the user is redirected to the overview page
    And the page shell is visible

  @saas @SA-02 @smoke
  Scenario: New user signs up and account is created successfully
    Given the user is not logged in and is on the signup page
    When the user submits the signup form with a new email and password
    Then the account is created and the user lands on the overview page

  @saas @SA-04 @SA-05 @smoke
  Scenario: Expired JWT causes redirect to the login page
    Given the user is logged in via JWT injection
    When the user navigates to the overview page
    And the session token expires
    Then the user is redirected to the login page

  @saas @SA-13 @smoke
  Scenario: The signup route renders as a full-page layout without the app shell
    Given the user is not logged in and is on the signup page
    Then the page shell is not visible
    And the signup form is visible

  @saas @SA-13
  Scenario: The upgrade route renders as a full-page layout without the app shell
    Given the user is logged in via JWT injection
    When the user navigates to the upgrade page
    Then the page shell is not visible
    And the upgrade page content is visible
