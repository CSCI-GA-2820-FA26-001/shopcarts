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
from datetime import datetime
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

    ######################################################################
    #  U P D A T E   A   S H O P C A R T   (#6)
    ######################################################################

    def test_update_shopcart(self):
        """It should Update a Shopcart"""
        created = self.client.post("/shopcarts", json={"user_id": 123}).get_json()

        response = self.client.put(f"/shopcarts/{created['id']}", json={"user_id": 456})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["id"], created["id"])
        self.assertEqual(data["user_id"], 456)
        self.assertEqual(data["created_at"], created["created_at"])

        response = self.client.get(f"/shopcarts/{created['id']}")
        self.assertEqual(response.get_json()["user_id"], 456)
        self.assertEqual(len(Shopcart.all()), 1)

    def test_update_shopcart_replaces_items(self):
        """It should replace the Items of a Shopcart"""
        payload = {
            "user_id": 123,
            "items": [
                {"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99},
                {"product_id": 1002, "name": "Product B", "quantity": 1, "price": 5.00},
            ],
        }
        created = self.client.post("/shopcarts", json=payload).get_json()

        payload["items"] = [
            {"product_id": 1001, "name": "Product A", "quantity": 5, "price": 24.99},
        ]
        response = self.client.put(f"/shopcarts/{created['id']}", json=payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["product_id"], 1001)
        self.assertEqual(data["items"][0]["quantity"], 5)
        self.assertEqual(data["items"][0]["shopcart_id"], created["id"])
        self.assertEqual(len(Item.all()), 1)

    def test_update_shopcart_empty_items(self):
        """It should remove every Item when Updated with an empty Items list"""
        payload = {
            "user_id": 123,
            "items": [{"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99}],
        }
        created = self.client.post("/shopcarts", json=payload).get_json()

        response = self.client.put(f"/shopcarts/{created['id']}", json={"user_id": 123, "items": []})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["items"], [])
        self.assertEqual(len(Item.all()), 0)

    def test_update_shopcart_without_items(self):
        """It should keep the Items when Updated without an Items list"""
        payload = {
            "user_id": 123,
            "items": [{"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99}],
        }
        created = self.client.post("/shopcarts", json=payload).get_json()

        response = self.client.put(f"/shopcarts/{created['id']}", json={"user_id": 456})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["user_id"], 456)
        self.assertEqual(data["items"], created["items"])

    def test_update_shopcart_last_updated(self):
        """It should refresh last_updated when only the Items change"""
        created = self.client.post("/shopcarts", json={"user_id": 123}).get_json()
        payload = {
            "user_id": 123,
            "items": [{"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99}],
        }

        response = self.client.put(f"/shopcarts/{created['id']}", json=payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertGreater(
            datetime.fromisoformat(data["last_updated"]),
            datetime.fromisoformat(created["last_updated"]),
        )
        self.assertEqual(data["created_at"], created["created_at"])

    def test_update_shopcart_ignores_id(self):
        """It should not change the id of a Shopcart"""
        created = self.client.post("/shopcarts", json={"user_id": 123}).get_json()

        response = self.client.put(
            f"/shopcarts/{created['id']}",
            json={"id": created["id"] + 1000, "user_id": 456},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["id"], created["id"])
        self.assertIsNone(Shopcart.find(created["id"] + 1000))

    def test_update_shopcart_not_found(self):
        """It should not Update a Shopcart that does not exist"""
        response = self.client.put("/shopcarts/0", json={"user_id": 456})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("Shopcart with id '0' could not be found", data["message"])
        self.assertEqual(len(Shopcart.all()), 0)

    def test_update_shopcart_missing_user_id(self):
        """It should not Update a Shopcart without a user_id"""
        created = self.client.post("/shopcarts", json={"user_id": 123}).get_json()

        response = self.client.put(f"/shopcarts/{created['id']}", json={"items": []})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.get_json()["error"], "Bad Request")
        self.assertEqual(Shopcart.find(created["id"]).user_id, 123)

    def test_update_shopcart_bad_item(self):
        """It should not Update a Shopcart when an Item is invalid"""
        payload = {
            "user_id": 123,
            "items": [{"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99}],
        }
        created = self.client.post("/shopcarts", json=payload).get_json()

        payload = {
            "user_id": 456,
            "items": [{"product_id": 1002, "name": "Product B", "quantity": 0, "price": 5.00}],
        }
        response = self.client.put(f"/shopcarts/{created['id']}", json=payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.get(f"/shopcarts/{created['id']}")
        self.assertEqual(response.get_json()["user_id"], 123)
        self.assertEqual(response.get_json()["items"], created["items"])

    def test_update_shopcart_unsupported_media_type(self):
        """It should not Update a Shopcart without a JSON content type"""
        created = self.client.post("/shopcarts", json={"user_id": 123}).get_json()

        response = self.client.put(
            f"/shopcarts/{created['id']}",
            data='{"user_id": 456}',
            content_type="text/plain",
        )

        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        self.assertEqual(Shopcart.find(created["id"]).user_id, 123)

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

    ######################################################################
    #  D E L E T E   A   S H O P C A R T   (#7)
    ######################################################################

    def test_delete_shopcart(self):
        """It should Delete a Shopcart"""
        shopcart = Shopcart(user_id=123)
        shopcart.create()
        shopcart_id = shopcart.id

        response = self.client.delete(f"/shopcarts/{shopcart_id}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.data), 0)
        self.assertIsNone(Shopcart.find(shopcart_id))

        response = self.client.get(f"/shopcarts/{shopcart_id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_shopcart_with_items(self):
        """It should Delete a Shopcart and its Items"""
        payload = {
            "user_id": 123,
            "items": [
                {"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99},
                {"product_id": 1002, "name": "Product B", "quantity": 1, "price": 5.00},
            ],
        }
        created = self.client.post("/shopcarts", json=payload).get_json()
        self.assertEqual(len(Item.all()), 2)

        response = self.client.delete(f"/shopcarts/{created['id']}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(Shopcart.find(created["id"]))
        self.assertEqual(len(Item.all()), 0)

    def test_delete_shopcart_leaves_others(self):
        """It should only Delete the requested Shopcart"""
        keep = self.client.post(
            "/shopcarts",
            json={
                "user_id": 1,
                "items": [{"product_id": 1001, "name": "Kept", "quantity": 1, "price": 1.00}],
            },
        ).get_json()
        remove = self.client.post("/shopcarts", json={"user_id": 2}).get_json()

        response = self.client.delete(f"/shopcarts/{remove['id']}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual([cart.id for cart in Shopcart.all()], [keep["id"]])
        self.assertEqual(len(Item.all()), 1)

    def test_delete_shopcart_not_found(self):
        """It should not Delete a Shopcart that does not exist"""
        response = self.client.delete("/shopcarts/0")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("Shopcart with id '0' could not be found", data["message"])

    ######################################################################
    #  L I S T   S H O P C A R T S   (#8)
    ######################################################################

    def test_list_shopcarts(self):
        """It should List all Shopcarts"""
        for user_id in (1, 2, 3):
            self.client.post("/shopcarts", json={"user_id": user_id})

        response = self.client.get("/shopcarts")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 3)
        self.assertEqual(sorted(cart["user_id"] for cart in data), [1, 2, 3])

    def test_list_shopcarts_with_items(self):
        """It should List Shopcarts with their Items"""
        item = {"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99}
        created = self.client.post(
            "/shopcarts", json={"user_id": 1, "items": [item]}
        ).get_json()

        response = self.client.get("/shopcarts")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], created["id"])
        self.assertEqual(len(data[0]["items"]), 1)
        self.assertEqual(data[0]["items"][0]["product_id"], 1001)

    def test_list_shopcarts_empty(self):
        """It should return an empty list when there are no Shopcarts"""
        response = self.client.get("/shopcarts")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), [])

    ######################################################################
    #  L I S T   I T E M S   I N   A   S H O P C A R T   (#12)
    ######################################################################

    def test_list_items(self):
        """It should List all Items in a Shopcart"""
        items = [
            {"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99},
            {"product_id": 1002, "name": "Product B", "quantity": 1, "price": 5.00},
        ]
        created = self.client.post(
            "/shopcarts", json={"user_id": 1, "items": items}
        ).get_json()

        response = self.client.get(f"/shopcarts/{created['id']}/items")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 2)
        self.assertEqual([item["product_id"] for item in data], [1001, 1002])
        for item in data:
            self.assertEqual(item["shopcart_id"], created["id"])
            for field in ("id", "name", "quantity", "price"):
                self.assertIn(field, item)

    def test_list_items_empty(self):
        """It should return an empty list for a Shopcart with no Items"""
        created = self.client.post("/shopcarts", json={"user_id": 1}).get_json()

        response = self.client.get(f"/shopcarts/{created['id']}/items")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), [])

    def test_list_items_only_from_that_shopcart(self):
        """It should only List the Items of the Shopcart in the URL"""
        item = {"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99}
        first = self.client.post(
            "/shopcarts", json={"user_id": 1, "items": [item]}
        ).get_json()
        self.client.post(
            "/shopcarts", json={"user_id": 2, "items": [item, item]}
        )

        response = self.client.get(f"/shopcarts/{first['id']}/items")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["shopcart_id"], first["id"])

    def test_list_items_shopcart_not_found(self):
        """It should not List Items of a Shopcart that does not exist"""
        response = self.client.get("/shopcarts/0/items")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("Shopcart with id '0' could not be found", data["message"])
