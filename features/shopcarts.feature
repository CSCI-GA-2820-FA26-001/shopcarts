Feature: The shopcarts service back-end
    As a Store Manager
    I need a RESTful shopcarts service
    So that I can keep track of my customers' shopcarts

Background:
    Given the following shopcarts
        | user_id |
        | 101     |
        | 202     |
    And the following items in the shopcart of customer "101"
        | product_id | name     | quantity | price |
        | 1001       | Notebook | 2        | 12.99 |

Scenario: The admin page loads
    When I visit the "Home Page"
    Then I should see "Shopcarts Admin" in the title
    And I should not see "404 Not Found"
    And I should see the "User ID" field and the "Search" button

Scenario: Clear the form
    When I visit the "Home Page"
    And I set the "User ID" to "101"
    And I press the "Clear" button
    Then the "User ID" field should be empty
