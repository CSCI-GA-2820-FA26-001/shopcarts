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
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_shopcart(self, user_id=1):
        """Creates a Shopcart directly in the database"""
        shopcart = Shopcart(user_id=user_id)
        shopcart.create()
        return shopcart

    ######################################################################
    #  P L A C E   T E S T   C A S E S   H E R E
    ######################################################################

    def test_index(self):
        """It should return information about the service at the root URL"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], "Shopcart REST API Service")
        self.assertEqual(data["version"], "1.0")
        self.assertTrue(data["paths"].endswith("/shopcarts"))

    ######################################################################
    #  H E A L T H   C H E C K   (#26)
    ######################################################################

    def test_health(self):
        """It should report that the service is healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), {"status": "OK"})

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
                {
                    "product_id": 1001,
                    "name": "Product A",
                    "quantity": 2,
                    "price": 24.99,
                },
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
                {
                    "product_id": 1001,
                    "name": "Product A",
                    "quantity": 2,
                    "price": 24.99,
                },
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
            "items": [
                {"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99}
            ],
        }
        created = self.client.post("/shopcarts", json=payload).get_json()

        response = self.client.put(
            f"/shopcarts/{created['id']}", json={"user_id": 123, "items": []}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["items"], [])
        self.assertEqual(len(Item.all()), 0)

    def test_update_shopcart_without_items(self):
        """It should keep the Items when Updated without an Items list"""
        payload = {
            "user_id": 123,
            "items": [
                {"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99}
            ],
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
            "items": [
                {"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99}
            ],
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
            "items": [
                {"product_id": 1001, "name": "Product A", "quantity": 2, "price": 24.99}
            ],
        }
        created = self.client.post("/shopcarts", json=payload).get_json()

        payload = {
            "user_id": 456,
            "items": [
                {"product_id": 1002, "name": "Product B", "quantity": 0, "price": 5.00}
            ],
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
                {
                    "product_id": 1001,
                    "name": "Product A",
                    "quantity": 2,
                    "price": 24.99,
                },
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
                "items": [
                    {"product_id": 1001, "name": "Kept", "quantity": 1, "price": 1.00}
                ],
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
    #  Q U E R Y   S H O P C A R T S   B Y   U S E R   (#25)
    ######################################################################

    def test_query_shopcarts_by_user_id(self):
        """It should List only the Shopcarts of the given user_id"""
        for user_id in (1, 1, 2):
            self.client.post("/shopcarts", json={"user_id": user_id})

        response = self.client.get("/shopcarts", query_string={"user_id": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 2)
        self.assertTrue(all(cart["user_id"] == 1 for cart in data))

    def test_query_shopcarts_by_user_id_no_match(self):
        """It should return an empty list when the user has no Shopcarts"""
        self.client.post("/shopcarts", json={"user_id": 1})

        response = self.client.get("/shopcarts", query_string={"user_id": 3})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), [])

    def test_query_shopcarts_by_bad_user_id(self):
        """It should not List Shopcarts when user_id is not an integer"""
        self.client.post("/shopcarts", json={"user_id": 1})
        for bad in ("abc", "1.5", ""):
            with self.subTest(user_id=bad):
                response = self.client.get("/shopcarts", query_string={"user_id": bad})

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.get_json()["error"], "Bad Request")

    ######################################################################
    #  A D D   I T E M   T O   S H O P C A R T   (#9)
    ######################################################################

    def test_add_item(self):
        """It should Add an Item to a Shopcart"""
        shopcart = self._create_shopcart()
        payload = make_item()
        resp = self.client.post(f"{BASE_URL}/{shopcart.id}/items", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        data = resp.get_json()
        self.assertIsNotNone(data["id"])
        self.assertEqual(data["shopcart_id"], shopcart.id)
        self.assertEqual(data["product_id"], payload["product_id"])
        self.assertEqual(data["name"], payload["name"])
        self.assertEqual(data["quantity"], payload["quantity"])
        self.assertAlmostEqual(float(data["price"]), payload["price"])

        location = resp.headers.get("Location")
        self.assertTrue(
            location.endswith(f"/shopcarts/{shopcart.id}/items/{data['id']}")
        )

        found = Shopcart.find(shopcart.id)
        self.assertEqual(len(found.items), 1)
        self.assertEqual(found.items[0].id, data["id"])

    def test_add_item_shopcart_not_found(self):
        """It should not Add an Item to a Shopcart that does not exist"""
        resp = self.client.post(f"{BASE_URL}/0/items", json=make_item())
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(db.session.query(Item).count(), 0)

    def test_add_item_missing_product_id(self):
        """It should not Add an Item without a product_id"""
        shopcart = self._create_shopcart()
        payload = make_item()
        del payload["product_id"]
        resp = self.client.post(f"{BASE_URL}/{shopcart.id}/items", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(db.session.query(Item).count(), 0)

    def test_add_item_bad_quantity(self):
        """It should not Add an Item with a quantity of zero or less"""
        shopcart = self._create_shopcart()
        for quantity in (0, -5):
            with self.subTest(quantity=quantity):
                resp = self.client.post(
                    f"{BASE_URL}/{shopcart.id}/items", json=make_item(quantity=quantity)
                )
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(db.session.query(Item).count(), 0)

    def test_add_item_bad_price(self):
        """It should not Add an Item with a negative price"""
        shopcart = self._create_shopcart()
        resp = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items", json=make_item(price=-1)
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(db.session.query(Item).count(), 0)

    def test_add_item_uses_url_shopcart(self):
        """It should put the Item in the Shopcart from the URL, not the body"""
        first = self._create_shopcart(user_id=1)
        second = self._create_shopcart(user_id=2)
        payload = make_item(shopcart_id=second.id)
        resp = self.client.post(f"{BASE_URL}/{first.id}/items", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.get_json()["shopcart_id"], first.id)
        self.assertEqual(len(Shopcart.find(second.id).items), 0)

    def test_add_item_wrong_content_type(self):
        """It should not Add an Item with the wrong Content-Type"""
        shopcart = self._create_shopcart()
        resp = self.client.post(
            f"{BASE_URL}/{shopcart.id}/items", data="name=x", content_type="text/html"
        )
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_delete_item(self):
        """It should delete an item without deleting its shopcart."""

        shopcart = self._create_shopcart()
        shopcart_id = shopcart.id

        item = Item()
        item.deserialize(make_item())
        item.shopcart_id = shopcart_id
        item.create()
        item_id = item.id

        response = self.client.delete(f"{BASE_URL}/{shopcart_id}/items/{item_id}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, b"")
        self.assertIsNone(Item.find(item_id))
        self.assertIsNotNone(Shopcart.find(shopcart_id))

    def test_delete_item_shopcart_not_found(self):
        """It should return 404 when the shopcart does not exist."""
        response = self.client.delete(f"{BASE_URL}/0/items/1")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_item_not_found(self):
        """It should return 404 when the item does not exist."""
        shopcart = self._create_shopcart()
        shopcart_id = shopcart.id

        response = self.client.delete(f"{BASE_URL}/{shopcart_id}/items/0")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIsNotNone(Shopcart.find(shopcart_id))

    def test_delete_item_wrong_shopcart(self):
        """It should not delete an item belonging to another shopcart."""
        first = self._create_shopcart(user_id=1)
        second = self._create_shopcart(user_id=2)
        first_id = first.id
        second_id = second.id

        item = Item()
        item.deserialize(make_item())
        item.shopcart_id = second_id
        item.create()
        item_id = item.id

        response = self.client.delete(f"{BASE_URL}/{first_id}/items/{item_id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        remaining = Item.find(item_id)
        self.assertIsNotNone(remaining)
        self.assertEqual(remaining.shopcart_id, second_id)
        self.assertIsNotNone(Shopcart.find(first_id))
        self.assertIsNotNone(Shopcart.find(second_id))

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
        self.client.post("/shopcarts", json={"user_id": 2, "items": [item, item]})

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

    ######################################################################
    # READ AN ITEM FROM A SHOPCART (#13)
    ######################################################################

    def test_read_item(self):
        """It should Read a specific Item from a Shopcart"""
        payload = make_item()
        created = self.client.post(
            BASE_URL,
            json={"user_id": 1, "items": [payload]},
        ).get_json()

        shopcart_id = created["id"]
        expected_item = created["items"][0]
        item_id = expected_item["id"]

        response = self.client.get(f"{BASE_URL}/{shopcart_id}/items/{item_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data, expected_item)

        for field in ("id", "shopcart_id", "product_id", "name", "quantity", "price"):
            self.assertIn(field, data)

    def test_read_item_not_found(self):
        """It should return 404 when the Item does not exist"""
        shopcart = self._create_shopcart()

        response = self.client.get(f"{BASE_URL}/{shopcart.id}/items/0")

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_read_item_shopcart_not_found(self):
        """It should return 404 when the Shopcart does not exist"""
        response = self.client.get(f"{BASE_URL}/0/items/1")

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_read_item_wrong_shopcart(self):
        """It should not Read an Item from another Shopcart"""
        first = self._create_shopcart(user_id=1)
        second = self.client.post(
            BASE_URL,
            json={"user_id": 2, "items": [make_item()]},
        ).get_json()

        item_id = second["items"][0]["id"]

        response = self.client.get(f"{BASE_URL}/{first.id}/items/{item_id}")

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
