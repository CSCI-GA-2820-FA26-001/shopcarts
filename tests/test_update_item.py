"""REST API tests for updating an Item in a Shopcart (#10)."""

import logging
from unittest import TestCase
from wsgi import app
from service.common import status
from service.models import db, Item, Shopcart


class TestUpdateItemService(TestCase):
    """Update Item REST API Tests"""

    @classmethod
    def setUpClass(cls):
        """Configure the app and establish the test context."""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.logger.setLevel(logging.CRITICAL)
        cls._app_context = app.app_context()
        cls._app_context.push()

    @classmethod
    def tearDownClass(cls):
        """Release the database session and test context."""
        db.session.remove()
        cls._app_context.pop()

    def setUp(self):
        """Create an existing Shopcart and Item before each test."""
        self.client = app.test_client()
        db.session.query(Item).delete()
        db.session.query(Shopcart).delete()
        db.session.commit()
        self.shopcart = Shopcart(user_id=1)
        self.shopcart.create()
        self.item = Item(
            shopcart_id=self.shopcart.id,
            product_id=1001,
            name="Notebook",
            quantity=2,
            price=12.99,
        )
        self.item.create()
        self.original = self.item.serialize()
        self.url = f"/shopcarts/{self.shopcart.id}/items/{self.item.id}"

    def tearDown(self):
        """Remove the session after each test."""
        db.session.remove()

    def _assert_item_unchanged(self):
        """Verify that a rejected request did not change persisted Item data."""
        db.session.expire_all()
        self.assertEqual(
            Item.find(self.original["id"]).serialize(), self.original
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), self.original)

    def test_update_item(self):
        """It should Update only the requested Item and persist the changes"""
        sibling = Item(
            shopcart_id=self.shopcart.id,
            product_id=1002,
            name="Pen",
            quantity=1,
            price=3.50,
        )
        sibling.create()
        sibling_data = sibling.serialize()
        payload = {
            "product_id": self.original["product_id"],
            "name": "Large notebook",
            "quantity": 5,
            "price": 9.99,
        }
        expected = dict(self.original, **payload)

        response = self.client.put(self.url, json=payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), expected)
        # Re-read from the database, not just the SQLAlchemy identity map.
        db.session.expire_all()
        self.assertEqual(Item.find(self.original["id"]).serialize(), expected)
        self.assertEqual(self.client.get(self.url).get_json(), expected)
        self.assertEqual(Item.find(sibling_data["id"]).serialize(), sibling_data)
        self.assertEqual(len(Item.all()), 2)
        self.assertEqual(len(Shopcart.all()), 1)
        self.assertEqual(len(Shopcart.find(self.original["shopcart_id"]).items), 2)

    def test_update_item_repeated_request(self):
        """It should not create another Item when the same update is repeated"""
        payload = dict(self.original, quantity=3, price=0)

        first = self.client.put(self.url, json=payload)
        second = self.client.put(self.url, json=payload)

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.get_json(), second.get_json())
        self.assertEqual(second.get_json(), payload)
        db.session.expire_all()
        self.assertEqual(Item.find(self.original["id"]).serialize(), payload)
        self.assertEqual(len(Item.all()), 1)

    def test_update_item_ignores_ids(self):
        """It should preserve the Item ID and Shopcart from the URL"""
        other = Shopcart(user_id=2)
        other.create()
        payload = dict(
            self.original, id=self.item.id + 1000, shopcart_id=other.id, quantity=4
        )

        response = self.client.put(self.url, json=payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected = dict(self.original, quantity=4)
        self.assertEqual(response.get_json(), expected)
        db.session.expire_all()
        self.assertEqual(Item.find(self.original["id"]).serialize(), expected)
        self.assertIsNone(Item.find(payload["id"]))
        self.assertEqual(len(Shopcart.find(other.id).items), 0)
        self.assertEqual(len(Item.all()), 1)

    def test_update_item_shopcart_not_found(self):
        """It should return 404 when updating an Item in a missing Shopcart"""
        response = self.client.put(
            f"/shopcarts/0/items/{self.item.id}", json=self.original
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self._assert_item_unchanged()

    def test_update_item_not_found(self):
        """It should return 404 rather than create a missing Item"""
        response = self.client.put(
            f"/shopcarts/{self.shopcart.id}/items/0", json=self.original
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(len(Item.all()), 1)
        self._assert_item_unchanged()

    def test_update_item_wrong_shopcart(self):
        """It should not Update an Item belonging to another Shopcart"""
        other = Shopcart(user_id=2)
        other.create()

        response = self.client.put(
            f"/shopcarts/{other.id}/items/{self.item.id}",
            json=dict(self.original, quantity=5),
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self._assert_item_unchanged()
        self.assertEqual(len(Shopcart.find(other.id).items), 0)

    def test_update_item_bad_quantity(self):
        """It should reject quantities that are not positive integers"""
        for quantity in (0, -1, 1.5, "2", True, None):
            with self.subTest(quantity=quantity):
                response = self.client.put(
                    self.url, json=dict(self.original, name="Changed", quantity=quantity)
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self._assert_item_unchanged()

    def test_update_item_bad_price(self):
        """It should reject invalid prices without saving any changes"""
        for price in (-1, "9.99", True, None, float("nan"), float("inf")):
            with self.subTest(price=price):
                response = self.client.put(
                    self.url, json=dict(self.original, quantity=5, price=price)
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self._assert_item_unchanged()

    def test_update_item_missing_fields(self):
        """It should require all Item data fields in the PUT payload"""
        for field in ("product_id", "name", "quantity", "price"):
            with self.subTest(field=field):
                payload = dict(self.original, quantity=5)
                del payload[field]
                response = self.client.put(self.url, json=payload)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self._assert_item_unchanged()

    def test_update_item_bad_product_data(self):
        """It should reject invalid product IDs and names"""
        for changes in ({"product_id": "1001"}, {"product_id": True}, {"name": ""}, {"name": 1}):
            with self.subTest(changes=changes):
                response = self.client.put(self.url, json=dict(self.original, **changes))
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self._assert_item_unchanged()

    def test_update_item_non_object_json(self):
        """It should reject JSON bodies that are not objects"""
        for body in ("null", "[]", '"item"', "7"):
            with self.subTest(body=body):
                response = self.client.put(
                    self.url, data=body, content_type="application/json"
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self._assert_item_unchanged()

    def test_update_item_invalid_json(self):
        """It should reject malformed or empty JSON"""
        for body in ('{"quantity":', ""):
            with self.subTest(body=body):
                response = self.client.put(
                    self.url, data=body, content_type="application/json"
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self._assert_item_unchanged()

    def test_update_item_wrong_content_type(self):
        """It should reject non-JSON content with 415"""
        response = self.client.put(
            self.url, data="quantity=5", content_type="text/plain"
        )

        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        self._assert_item_unchanged()
