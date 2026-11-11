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

"""
Shopcart Steps

Steps file for shopcarts.feature

These steps load the test data through the REST API, not the web page.
"""

# pylint: disable=function-redefined, not-callable
import requests
from behave import given, then  # pylint: disable=no-name-in-module

# HTTP Return Codes
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204

WAIT_TIMEOUT = 60

# The Shopcart routes move to /api/shopcarts in #54 and the Item routes in #59
SHOPCARTS_URL = "/shopcarts"
ITEMS_URL = "/shopcarts/{shopcart_id}/items"


@given("the following shopcarts")
def step_impl(context):
    """Delete all Shopcarts and load new ones"""
    rest_endpoint = f"{context.base_url}{SHOPCARTS_URL}"

    # Get a list of all of the Shopcarts and delete them one by one
    context.resp = requests.get(rest_endpoint, timeout=WAIT_TIMEOUT)
    assert context.resp.status_code == HTTP_200_OK
    for shopcart in context.resp.json():
        context.resp = requests.delete(f"{rest_endpoint}/{shopcart['id']}", timeout=WAIT_TIMEOUT)
        assert context.resp.status_code == HTTP_204_NO_CONTENT

    # Load the database with new Shopcarts
    for row in context.table:
        payload = {"user_id": int(row["user_id"])}
        context.resp = requests.post(rest_endpoint, json=payload, timeout=WAIT_TIMEOUT)
        assert context.resp.status_code == HTTP_201_CREATED


@given('the following items in the shopcart of customer "{user_id:d}"')
def step_impl(context, user_id):
    """Add Items to the Shopcart of a customer"""
    context.resp = requests.get(
        f"{context.base_url}{SHOPCARTS_URL}",
        params={"user_id": user_id},
        timeout=WAIT_TIMEOUT,
    )
    assert context.resp.status_code == HTTP_200_OK
    shopcarts = context.resp.json()
    assert len(shopcarts) == 1, f"Expected 1 shopcart for customer {user_id}, found {len(shopcarts)}"

    rest_endpoint = context.base_url + ITEMS_URL.format(shopcart_id=shopcarts[0]["id"])
    for row in context.table:
        payload = {
            "product_id": int(row["product_id"]),
            "name": row["name"],
            "quantity": int(row["quantity"]),
            "price": float(row["price"]),
        }
        context.resp = requests.post(rest_endpoint, json=payload, timeout=WAIT_TIMEOUT)
        assert context.resp.status_code == HTTP_201_CREATED


@then('the shopcart of customer "{user_id:d}" should have {count:d} item')
@then('the shopcart of customer "{user_id:d}" should have {count:d} items')
def step_impl(context, user_id, count):
    """Check the number of Items in the Shopcart of a customer through the REST API"""
    context.resp = requests.get(
        f"{context.base_url}{SHOPCARTS_URL}",
        params={"user_id": user_id},
        timeout=WAIT_TIMEOUT,
    )
    assert context.resp.status_code == HTTP_200_OK
    shopcarts = context.resp.json()
    assert len(shopcarts) == 1, f"Expected 1 shopcart for customer {user_id}, found {len(shopcarts)}"
    items = shopcarts[0]["items"]
    assert len(items) == count, f"Expected {count} items, found {len(items)}"
