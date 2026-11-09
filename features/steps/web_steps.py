######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

# pylint: disable=function-redefined, missing-function-docstring, not-callable
"""
Web Steps

Steps file for web interactions with Selenium

For information on Waiting until elements are present in the HTML see:
    https://selenium-python.readthedocs.io/waits.html
"""
import logging
from behave import when, then  # pylint: disable=no-name-in-module
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

# The ids of the admin page from #64
ID_PREFIX = "shopcart_"
FLASH_MESSAGE_ID = "flash_message"
RESULTS_TABLE_ID = "search_results"
# The results table has the columns Shopcart ID, User ID and Status
USER_ID_COLUMN = 2


def field_id(element_name: str) -> str:
    """Turns a field label like "User ID" into its id, shopcart_user_id"""
    element_id = element_name.lower().replace(" ", "_")
    if not element_id.startswith(ID_PREFIX):
        element_id = ID_PREFIX + element_id
    return element_id


def button_id(button: str) -> str:
    """Turns a button label like "Search" into its id, search-btn"""
    return button.lower().replace(" ", "-") + "-btn"


def result_user_ids(context) -> list:
    """Returns the User ID of every row in the results table"""
    cells = context.driver.find_elements(
        By.CSS_SELECTOR, f"#{RESULTS_TABLE_ID} tbody tr td:nth-child({USER_ID_COLUMN})"
    )
    return [cell.text.strip() for cell in cells]


def wait_for(context, condition, message):
    """Waits until condition(driver) is true, failing with message after the wait time"""
    return WebDriverWait(context.driver, context.wait_seconds).until(condition, message)


######################################################################
# P A G E   S T E P S
######################################################################


@when('I visit the "Home Page"')
def step_impl(context):
    """Make a call to the base URL"""
    context.driver.get(context.base_url)


@then('I should see "{message}" in the title')
def step_impl(context, message):
    """Check the document title for a message"""
    assert message in context.driver.title


@then('I should not see "{text_string}"')
def step_impl(context, text_string):
    element = context.driver.find_element(By.TAG_NAME, "body")
    assert text_string not in element.text


@then('I should see the "{element_name}" field and the "{button}" button')
def step_impl(context, element_name, button):
    for element_id in (field_id(element_name), button_id(button)):
        element = wait_for(
            context,
            expected_conditions.visibility_of_element_located((By.ID, element_id)),
            f'"{element_id}" was not on the page',
        )
        assert element.is_enabled()


######################################################################
# F O R M   S T E P S
######################################################################


@when('I set the "{element_name}" to "{text_string}"')
def step_impl(context, element_name, text_string):
    element = context.driver.find_element(By.ID, field_id(element_name))
    element.clear()
    element.send_keys(text_string)


@when('I press the "{button}" button')
def step_impl(context, button):
    context.driver.find_element(By.ID, button_id(button)).click()


@then('I should see the message "{message}"')
def step_impl(context, message):
    found = wait_for(
        context,
        expected_conditions.text_to_be_present_in_element((By.ID, FLASH_MESSAGE_ID), message),
        f'The message "{message}" was not shown',
    )
    assert found


@then('the "{element_name}" field should be empty')
def step_impl(context, element_name):
    element = context.driver.find_element(By.ID, field_id(element_name))
    assert element.get_attribute("value") == ""


@then('the "{element_name}" field should contain "{text_string}"')
def step_impl(context, element_name, text_string):
    found = wait_for(
        context,
        expected_conditions.text_to_be_present_in_element_value((By.ID, field_id(element_name)), text_string),
        f'The "{element_name}" field did not contain "{text_string}"',
    )
    assert found


##################################################################
# These two functions simulate copy and paste
##################################################################
@when('I copy the "{element_name}" field')
def step_impl(context, element_name):
    element = wait_for(
        context,
        expected_conditions.presence_of_element_located((By.ID, field_id(element_name))),
        f'The "{element_name}" field was not found',
    )
    context.clipboard = element.get_attribute("value")
    logging.info("Clipboard contains: %s", context.clipboard)


@when('I paste the "{element_name}" field')
def step_impl(context, element_name):
    element = wait_for(
        context,
        expected_conditions.presence_of_element_located((By.ID, field_id(element_name))),
        f'The "{element_name}" field was not found',
    )
    element.clear()
    element.send_keys(context.clipboard)


######################################################################
# R E S U L T S   S T E P S
#
# Shopcart IDs keep growing between runs, so these compare the
# User ID column exactly instead of searching the whole table text.
######################################################################


@then('I should see "{user_id}" in the results')
def step_impl(context, user_id):
    found = wait_for(
        context,
        lambda _: user_id in result_user_ids(context),
        f'User ID "{user_id}" was not in the results',
    )
    assert found


@then('I should not see "{user_id}" in the results')
def step_impl(context, user_id):
    user_ids = result_user_ids(context)
    assert user_id not in user_ids, f'User ID "{user_id}" was in the results: {user_ids}'


@then("I should see {count:d} shopcarts in the results")
def step_impl(context, count):
    found = wait_for(
        context,
        lambda _: len(result_user_ids(context)) == count,
        f"There were not {count} shopcarts in the results",
    )
    assert found
