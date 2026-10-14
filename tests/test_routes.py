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
TestYourResourceModel API Service Test Suite
"""

# pylint: disable=duplicate-code
import os
import logging
from unittest import TestCase
from wsgi import app
from service.common import status
from service.models import db, Shopcart, Item

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestYourResourceService(TestCase):
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
    #  P L A C E   T E S T   C A S E S   H E R E
    ######################################################################

    def test_index(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    ######################################################################
    #  R E A D   A   S H O P C A R T   (#5)
    ######################################################################

    def test_get_shopcart(self):
        """It should Read a Shopcart"""
        shopcart = Shopcart(user_id=123)
        shopcart.create()

        response = self.client.get(f"/shopcarts/{shopcart.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["id"], shopcart.id)
        self.assertEqual(data["user_id"], 123)
        self.assertEqual(data["items"], [])
        self.assertIsNotNone(data["created_at"])
        self.assertIsNotNone(data["last_updated"])

    def test_get_shopcart_with_items(self):
        """It should Read a Shopcart and its Items"""
        payload = {
            "user_id": 123,
            "items": [
                {"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99},
                {"product_id": 1002, "name": "Product B", "quantity": 1, "price": 5.00},
            ],
        }
        created = self.client.post("/shopcarts", json=payload).get_json()

        response = self.client.get(f"/shopcarts/{created['id']}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["id"], created["id"])
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual([item["product_id"] for item in data["items"]], [1001, 1002])
        for item in data["items"]:
            self.assertEqual(item["shopcart_id"], created["id"])

    def test_get_shopcart_from_location(self):
        """It should Read a Shopcart at the Location returned by Create"""
        response = self.client.post("/shopcarts", json={"user_id": 123})
        location = response.headers["Location"]

        response = self.client.get(location)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["user_id"], 123)

    def test_get_shopcart_not_found(self):
        """It should not Read a Shopcart that does not exist"""
        response = self.client.get("/shopcarts/0")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("Shopcart with id '0' could not be found", data["message"])

    def test_create_shopcart(self):
        """It should Create a Shopcart"""
        payload = {"user_id": 123}

        response = self.client.post("/shopcarts", json=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.get_json()
        self.assertIsNotNone(data["id"])
        self.assertEqual(data["user_id"], 123)
        self.assertEqual(data["items"], [])

        self.assertIn("Location", response.headers)
        self.assertTrue(
            response.headers["Location"].endswith(f"/shopcarts/{data['id']}")
        )

        shopcart = Shopcart.find(data["id"])
        self.assertIsNotNone(shopcart)
        self.assertEqual(shopcart.user_id, 123)

    def test_create_shopcart_with_items(self):
        """It should Create a Shopcart with initial Items"""
        payload = {
            "user_id": 123,
            "items": [
                {
                    "product_id": 1001,
                    "name": "Product A",
                    "quantity": 2,
                    "price": 24.99,
                }
            ],
        }

        response = self.client.post("/shopcarts", json=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.get_json()
        self.assertEqual(len(data["items"]), 1)

        item = data["items"][0]
        self.assertIsNotNone(item["id"])
        self.assertEqual(item["shopcart_id"], data["id"])
        self.assertEqual(item["product_id"], 1001)
        self.assertEqual(item["quantity"], 2)

        saved_cart = Shopcart.find(data["id"])
        self.assertIsNotNone(saved_cart)
        self.assertEqual(len(saved_cart.items), 1)

    def test_create_shopcart_missing_user_id(self):
        """It should not Create a Shopcart without a user_id"""
        payload = {"items": []}

        response = self.client.post("/shopcarts", json=payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(Shopcart.all()), 0)

    def test_create_shopcart_invalid_quantity(self):
        """It should reject a Shopcart with an invalid Item quantity"""
        for quantity in (0, -1):
            with self.subTest(quantity=quantity):
                payload = {
                    "user_id": 123,
                    "items": [
                        {
                            "product_id": 1001,
                            "name": "Product A",
                            "quantity": quantity,
                            "price": 24.99,
                        }
                    ],
                }

                response = self.client.post("/shopcarts", json=payload)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(len(Shopcart.all()), 0)
                self.assertEqual(len(Item.all()), 0)

    def test_create_shopcart_negative_price(self):
        """It should reject a Shopcart with a negative Item price"""
        payload = {
            "user_id": 123,
            "items": [
                {
                    "product_id": 1001,
                    "name": "Product A",
                    "quantity": 2,
                    "price": -10.00,
                }
            ],
        }

        response = self.client.post("/shopcarts", json=payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(Shopcart.all()), 0)
        self.assertEqual(len(Item.all()), 0)

    def test_create_shopcart_atomicity(self):
        """It should not persist a Shopcart when one Item is invalid"""
        payload = {
            "user_id": 123,
            "items": [
                {
                    "product_id": 1001,
                    "name": "Valid Product",
                    "quantity": 2,
                    "price": 24.99,
                },
                {
                    "product_id": 1002,
                    "name": "Invalid Product",
                    "quantity": 0,
                    "price": 15.00,
                },
            ],
        }

        response = self.client.post("/shopcarts", json=payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(Shopcart.all()), 0)
        self.assertEqual(len(Item.all()), 0)

    def test_create_empty_shopcart(self):
        """It should Create a Shopcart with an empty Items list"""
        payload = {
            "user_id": 123,
            "items": [],
        }

        response = self.client.post("/shopcarts", json=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.get_json()
        self.assertIsNotNone(data["id"])
        self.assertEqual(data["user_id"], 123)
        self.assertEqual(data["items"], [])

        self.assertIn("Location", response.headers)
        self.assertTrue(
            response.headers["Location"].endswith(f"/shopcarts/{data['id']}")
        )

        saved_cart = Shopcart.find(data["id"])
        self.assertIsNotNone(saved_cart)
        self.assertEqual(len(saved_cart.items), 0)

    def test_create_shopcart_invalid_json(self):
        """It should reject malformed JSON"""
        response = self.client.post(
            "/shopcarts",
            data='{"user_id":',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.get_json()["error"], "Bad Request")
        self.assertEqual(len(Shopcart.all()), 0)

    def test_create_shopcart_unsupported_media_type(self):
        """It should reject a request without JSON content type"""
        response = self.client.post(
            "/shopcarts",
            data='{"user_id": 123}',
            content_type="text/plain",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )
        self.assertEqual(
            response.get_json()["error"],
            "Unsupported media type",
        )
        self.assertEqual(len(Shopcart.all()), 0)

    def test_create_shopcart_method_not_allowed(self):
        """It should reject an unsupported method on the Shopcarts collection"""
        response = self.client.put(
            "/shopcarts",
            json={"user_id": 123},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            response.get_json()["error"],
            "Method not Allowed",
        )
        self.assertEqual(len(Shopcart.all()), 0)
