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
Shopcart API Service Test Suite
"""

# pylint: disable=duplicate-code
import os
import logging
from unittest import TestCase
from wsgi import app
from service.common import status
from service.models import db, Shopcart, Item

DATABASE_URI = os.getenv("DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb")
BASE_URL = "/shopcarts"


def make_item(**overrides):
    """Returns a valid Item payload, with any fields overridden"""
    data = {"product_id": 1001, "name": "Vinyl record", "quantity": 2, "price": 24.99}
    data.update(overrides)
    return data


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestShopcartService(TestCase):
    """REST API Server Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        # Items reference Shopcarts, so they are removed first
        db.session.query(Item).delete()
        db.session.query(Shopcart).delete()
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _assert_nothing_saved(self):
        """Asserts that no Shopcart and no Item rows exist"""
        self.assertEqual(db.session.query(Shopcart).count(), 0)
        self.assertEqual(db.session.query(Item).count(), 0)

    ######################################################################
    #  P L A C E   T E S T   C A S E S   H E R E
    ######################################################################

    def test_index(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    ######################################################################
    #  C R E A T E   S H O P C A R T   (#4)
    ######################################################################

    def test_create_shopcart(self):
        """It should Create a Shopcart"""
        resp = self.client.post(BASE_URL, json={"user_id": 7})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        data = resp.get_json()
        self.assertIsNotNone(data["id"])
        self.assertEqual(data["user_id"], 7)
        self.assertEqual(data["items"], [])

        location = resp.headers.get("Location")
        self.assertTrue(location.endswith(f"/shopcarts/{data['id']}"))

        found = Shopcart.find(data["id"])
        self.assertIsNotNone(found)
        self.assertEqual(found.user_id, 7)

    def test_create_shopcart_with_items(self):
        """It should Create a Shopcart with initial Items"""
        items = [make_item(), make_item(product_id=2002, name="Concert ticket", quantity=1, price=89.5)]
        resp = self.client.post(BASE_URL, json={"user_id": 7, "items": items})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        data = resp.get_json()
        self.assertEqual(len(data["items"]), 2)
        for sent, returned in zip(items, data["items"]):
            self.assertIsNotNone(returned["id"])
            self.assertEqual(returned["shopcart_id"], data["id"])
            self.assertEqual(returned["product_id"], sent["product_id"])
            self.assertEqual(returned["name"], sent["name"])
            self.assertEqual(returned["quantity"], sent["quantity"])
            self.assertAlmostEqual(float(returned["price"]), sent["price"])

        self.assertEqual(db.session.query(Item).count(), 2)
        found = Shopcart.find(data["id"])
        self.assertEqual(len(found.items), 2)

    def test_create_empty_shopcart(self):
        """It should Create a Shopcart when the Item list is empty"""
        resp = self.client.post(BASE_URL, json={"user_id": 7, "items": []})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.get_json()["items"], [])
        self.assertEqual(db.session.query(Shopcart).count(), 1)

    def test_create_shopcart_ignores_client_id(self):
        """It should not let the client choose the Shopcart id"""
        resp = self.client.post(BASE_URL, json={"id": 999999, "user_id": 7})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(resp.get_json()["id"], 999999)

    def test_create_shopcart_missing_user_id(self):
        """It should not Create a Shopcart without a user_id"""
        resp = self.client.post(BASE_URL, json={"items": [make_item()]})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self._assert_nothing_saved()

    def test_create_shopcart_bad_quantity(self):
        """It should not Create a Shopcart with an Item quantity of zero or less"""
        for quantity in (0, -1):
            with self.subTest(quantity=quantity):
                resp = self.client.post(BASE_URL, json={"user_id": 7, "items": [make_item(quantity=quantity)]})
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
                self._assert_nothing_saved()

    def test_create_shopcart_bad_price(self):
        """It should not Create a Shopcart with a negative Item price"""
        resp = self.client.post(BASE_URL, json={"user_id": 7, "items": [make_item(price=-0.01)]})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self._assert_nothing_saved()

    def test_create_shopcart_no_partial_save(self):
        """It should save nothing when one of several Items is invalid"""
        items = [make_item(), make_item(product_id=2002, quantity=0)]
        resp = self.client.post(BASE_URL, json={"user_id": 7, "items": items})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self._assert_nothing_saved()

    def test_create_shopcart_not_an_object(self):
        """It should not Create a Shopcart from a body that is not a JSON object"""
        resp = self.client.post(BASE_URL, json=["user_id", 7])
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self._assert_nothing_saved()

    def test_create_shopcart_no_content_type(self):
        """It should not Create a Shopcart with no Content-Type"""
        resp = self.client.post(BASE_URL, data='{"user_id": 7}')
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_shopcart_wrong_content_type(self):
        """It should not Create a Shopcart with the wrong Content-Type"""
        resp = self.client.post(BASE_URL, data="user_id=7", content_type="text/html")
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
