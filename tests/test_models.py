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
Test cases for Shopcart and Item Models
"""

# pylint: disable=duplicate-code
import os
import logging
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch
from wsgi import app
from service.models import Shopcart, Item, DataValidationError, db
from .factories import ShopcartFactory, ItemFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)


def make_item_data(**overrides):
    """Returns a valid Item dictionary, with any fields overridden"""
    data = {"product_id": 1001, "name": "Vinyl record", "quantity": 2, "price": 24.99}
    data.update(overrides)
    return data


######################################################################
#  B A S E   T E S T   C A S E
######################################################################
class TestModelBase(TestCase):
    """Common setup for the model tests"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        # Items reference Shopcarts, so they are removed first
        db.session.query(Item).delete()
        db.session.query(Shopcart).delete()
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()


######################################################################
#  S H O P C A R T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestShopcartModel(TestModelBase):
    """Test Cases for the Shopcart Model"""

    def test_create_shopcart(self):
        """It should Create a Shopcart and assign it an id"""
        shopcart = Shopcart(user_id=7)
        shopcart.create()
        self.assertIsNotNone(shopcart.id)
        self.assertIsNotNone(shopcart.created_at)
        self.assertIsNotNone(shopcart.last_updated)

        found = Shopcart.find(shopcart.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.user_id, 7)

    def test_create_shopcart_ignores_id(self):
        """It should let the database choose the Shopcart id"""
        shopcart = ShopcartFactory(id=999999)
        shopcart.create()
        self.assertNotEqual(shopcart.id, 999999)

    def test_create_shopcart_without_user_id(self):
        """It should not Create a Shopcart without a user_id"""
        shopcart = Shopcart()
        self.assertRaises(DataValidationError, shopcart.create)
        self.assertEqual(len(Shopcart.all()), 0)

    def test_shopcart_with_no_items(self):
        """It should Read back a Shopcart with an empty Item list"""
        shopcart = ShopcartFactory()
        shopcart.create()
        found = Shopcart.find(shopcart.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.items, [])

    def test_shopcart_with_items(self):
        """It should Read back a Shopcart with its Items"""
        shopcart = ShopcartFactory()
        shopcart.items.append(Item(**make_item_data()))
        shopcart.items.append(
            Item(**make_item_data(product_id=2002, name="Concert ticket"))
        )
        shopcart.create()

        found = Shopcart.find(shopcart.id)
        self.assertEqual(len(found.items), 2)
        for item in found.items:
            self.assertIsNotNone(item.id)
            self.assertEqual(item.shopcart_id, shopcart.id)

    def test_list_all_shopcarts(self):
        """It should List all Shopcarts in the database"""
        self.assertEqual(Shopcart.all(), [])
        for _ in range(3):
            ShopcartFactory().create()
        self.assertEqual(len(Shopcart.all()), 3)

    def test_find_shopcart_not_found(self):
        """It should return None when a Shopcart is not found"""
        self.assertIsNone(Shopcart.find(0))

    def test_find_by_user_id(self):
        """It should Find only the Shopcarts that belong to a user"""
        for user_id in (1, 1, 2):
            ShopcartFactory(user_id=user_id).create()

        found = Shopcart.find_by_user_id(1)
        self.assertEqual(len(found), 2)
        for shopcart in found:
            self.assertEqual(shopcart.user_id, 1)

    def test_find_by_user_id_not_found(self):
        """It should return an empty list when a user has no Shopcarts"""
        ShopcartFactory(user_id=1).create()
        self.assertEqual(Shopcart.find_by_user_id(3), [])

    def test_update_shopcart(self):
        """It should Update a Shopcart"""
        shopcart = ShopcartFactory(user_id=1)
        shopcart.create()
        original_id = shopcart.id
        original_updated = shopcart.last_updated

        shopcart.user_id = 2
        shopcart.update()

        found = Shopcart.find(original_id)
        self.assertEqual(found.id, original_id)
        self.assertEqual(found.user_id, 2)
        self.assertGreaterEqual(found.last_updated, original_updated)
        self.assertEqual(len(Shopcart.all()), 1)

    def test_update_shopcart_items_only(self):
        """It should refresh last_updated when only the Items of a Shopcart change"""
        shopcart = ShopcartFactory()
        shopcart.create()
        original_updated = shopcart.last_updated

        shopcart.items.append(Item(**make_item_data()))
        shopcart.update()

        found = Shopcart.find(shopcart.id)
        self.assertEqual(len(found.items), 1)
        self.assertGreater(found.last_updated, original_updated)

    def test_update_shopcart_no_id(self):
        """It should not Update a Shopcart that has no id"""
        shopcart = ShopcartFactory()
        shopcart.id = None
        self.assertRaises(DataValidationError, shopcart.update)

    def test_update_shopcart_bad_data(self):
        """It should not Update a Shopcart with a missing user_id"""
        shopcart = ShopcartFactory()
        shopcart.create()
        shopcart.user_id = None
        self.assertRaises(DataValidationError, shopcart.update)

    def test_delete_shopcart(self):
        """It should Delete a Shopcart and its Items"""
        shopcart = ShopcartFactory()
        shopcart.items.append(Item(**make_item_data()))
        shopcart.create()
        self.assertEqual(len(Item.all()), 1)

        shopcart.delete()
        self.assertEqual(len(Shopcart.all()), 0)
        self.assertEqual(len(Item.all()), 0)

    def test_delete_shopcart_error(self):
        """It should raise a DataValidationError when a delete fails"""
        shopcart = ShopcartFactory()
        shopcart.create()
        with patch("service.models.db.session.commit", side_effect=Exception("boom")):
            self.assertRaises(DataValidationError, shopcart.delete)

    def test_serialize_shopcart(self):
        """It should Serialize a Shopcart with its Items"""
        shopcart = ShopcartFactory()
        shopcart.items.append(Item(**make_item_data()))
        shopcart.create()

        data = shopcart.serialize()
        self.assertEqual(data["id"], shopcart.id)
        self.assertEqual(data["user_id"], shopcart.user_id)
        self.assertEqual(data["created_at"], shopcart.created_at.isoformat())
        self.assertEqual(data["last_updated"], shopcart.last_updated.isoformat())
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["name"], "Vinyl record")
        self.assertEqual(data["items"][0]["shopcart_id"], shopcart.id)

    def test_deserialize_shopcart(self):
        """It should Deserialize a Shopcart with Items"""
        data = {
            "user_id": 7,
            "items": [make_item_data(), make_item_data(product_id=2002)],
        }
        shopcart = Shopcart().deserialize(data)
        self.assertEqual(shopcart.user_id, 7)
        self.assertEqual(len(shopcart.items), 2)
        self.assertEqual(shopcart.items[1].product_id, 2002)

    def test_deserialize_shopcart_without_items(self):
        """It should Deserialize a Shopcart that has no items key"""
        shopcart = Shopcart().deserialize({"user_id": 7})
        self.assertEqual(shopcart.user_id, 7)
        self.assertEqual(shopcart.items, [])

    def test_deserialize_ignores_server_fields(self):
        """It should ignore id, created_at and last_updated sent by a client"""
        data = {
            "id": 999,
            "user_id": 7,
            "created_at": "2000-01-01T00:00:00",
            "last_updated": "2000-01-01T00:00:00",
        }
        shopcart = Shopcart().deserialize(data)
        self.assertIsNone(shopcart.id)
        self.assertIsNone(shopcart.created_at)
        self.assertIsNone(shopcart.last_updated)

    def test_deserialize_shopcart_missing_user_id(self):
        """It should not Deserialize a Shopcart without a user_id"""
        self.assertRaises(DataValidationError, Shopcart().deserialize, {"items": []})

    def test_deserialize_shopcart_bad_user_id(self):
        """It should not Deserialize a Shopcart with a user_id that is not an integer"""
        for user_id in ("7", 7.5, None, True):
            with self.subTest(user_id=user_id):
                self.assertRaises(
                    DataValidationError, Shopcart().deserialize, {"user_id": user_id}
                )

    def test_deserialize_shopcart_not_a_dict(self):
        """It should not Deserialize a Shopcart from data that is not a dictionary"""
        for data in (None, "user_id", ["user_id", 7]):
            with self.subTest(data=data):
                self.assertRaises(DataValidationError, Shopcart().deserialize, data)

    def test_deserialize_shopcart_items_not_a_list(self):
        """It should not Deserialize a Shopcart whose items are not a list"""
        self.assertRaises(
            DataValidationError, Shopcart().deserialize, {"user_id": 7, "items": "nope"}
        )

    def test_deserialize_shopcart_bad_item(self):
        """It should not keep any Items when one of them is invalid"""
        shopcart = Shopcart()
        data = {"user_id": 7, "items": [make_item_data(), make_item_data(quantity=0)]}
        self.assertRaises(DataValidationError, shopcart.deserialize, data)
        self.assertEqual(shopcart.items, [])

    def test_shopcart_repr(self):
        """It should have a readable repr"""
        shopcart = ShopcartFactory(user_id=7)
        self.assertIn("user_id=7", repr(shopcart))


######################################################################
#  I T E M   M O D E L   T E S T   C A S E S
######################################################################
class TestItemModel(TestModelBase):
    """Test Cases for the Item Model"""

    def test_add_item_to_shopcart(self):
        """It should Add an Item to an existing Shopcart"""
        shopcart = ShopcartFactory()
        shopcart.create()

        item = Item(**make_item_data())
        item.shopcart_id = shopcart.id
        item.create()
        self.assertIsNotNone(item.id)

        found = Item.find(item.id)
        self.assertEqual(found.shopcart_id, shopcart.id)
        self.assertEqual(found.product_id, 1001)
        self.assertEqual(found.name, "Vinyl record")
        self.assertEqual(found.quantity, 2)
        self.assertEqual(found.price, Decimal("24.99"))
        self.assertEqual(len(Shopcart.find(shopcart.id).items), 1)

    def test_item_belongs_to_correct_shopcart(self):
        """It should keep an Item in the Shopcart it was added to"""
        first = ShopcartFactory()
        first.create()
        second = ShopcartFactory()
        second.create()

        item = ItemFactory(shopcart=first)
        item.create()

        found = Item.find(item.id)
        self.assertEqual(found.shopcart_id, first.id)
        self.assertEqual(len(Shopcart.find(first.id).items), 1)
        self.assertEqual(len(Shopcart.find(second.id).items), 0)

    def test_create_item_without_shopcart(self):
        """It should not Create an Item that does not belong to a Shopcart"""
        item = Item(**make_item_data())
        self.assertRaises(DataValidationError, item.create)
        self.assertEqual(len(Item.all()), 0)

    def test_create_item_bad_quantity(self):
        """It should not save an Item with a quantity of zero or less"""
        shopcart = ShopcartFactory()
        shopcart.create()
        for quantity in (0, -1):
            with self.subTest(quantity=quantity):
                item = ItemFactory(shopcart=shopcart, quantity=quantity)
                self.assertRaises(DataValidationError, item.create)
                self.assertEqual(len(Item.all()), 0)

    def test_create_item_bad_price(self):
        """It should not save an Item with a negative price"""
        shopcart = ShopcartFactory()
        shopcart.create()
        item = ItemFactory(shopcart=shopcart, price=Decimal("-0.01"))
        self.assertRaises(DataValidationError, item.create)
        self.assertEqual(len(Item.all()), 0)

    def test_update_item(self):
        """It should Update an Item"""
        item = ItemFactory()
        item.create()
        item.quantity = 5
        item.update()
        self.assertEqual(Item.find(item.id).quantity, 5)

    def test_delete_item(self):
        """It should Delete an Item without deleting its Shopcart"""
        item = ItemFactory()
        item.create()
        shopcart_id = item.shopcart_id

        item.delete()
        self.assertEqual(len(Item.all()), 0)
        found = Shopcart.find(shopcart_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.items, [])

    def test_serialize_item(self):
        """It should Serialize an Item"""
        item = ItemFactory()
        item.create()
        data = item.serialize()
        self.assertEqual(data["id"], item.id)
        self.assertEqual(data["shopcart_id"], item.shopcart_id)
        self.assertEqual(data["product_id"], item.product_id)
        self.assertEqual(data["name"], item.name)
        self.assertEqual(data["quantity"], item.quantity)
        self.assertEqual(data["price"], float(item.price))

    def test_deserialize_item(self):
        """It should Deserialize an Item"""
        item = Item().deserialize(make_item_data())
        self.assertEqual(item.product_id, 1001)
        self.assertEqual(item.name, "Vinyl record")
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.price, Decimal("24.99"))

    def test_deserialize_item_ignores_shopcart_id(self):
        """It should not move an Item to another Shopcart through deserialize"""
        item = ItemFactory()
        item.create()
        shopcart_id = item.shopcart_id
        other = ShopcartFactory()
        other.create()

        item.deserialize(make_item_data(quantity=9, shopcart_id=other.id))
        item.update()
        found = Item.find(item.id)
        self.assertEqual(found.shopcart_id, shopcart_id)
        self.assertEqual(found.quantity, 9)
        self.assertEqual(len(Shopcart.find(other.id).items), 0)

    def test_deserialize_shopcart_items_ignore_shopcart_id(self):
        """It should link nested Items to their own Shopcart"""
        data = {"user_id": 7, "items": [make_item_data(shopcart_id=999999)]}
        shopcart = Shopcart().deserialize(data)
        shopcart.create()
        self.assertEqual(Shopcart.find(shopcart.id).items[0].shopcart_id, shopcart.id)

    def test_deserialize_item_free(self):
        """It should Deserialize an Item with a price of zero"""
        item = Item().deserialize(make_item_data(price=0))
        self.assertEqual(item.price, Decimal("0"))

    def test_deserialize_item_missing_field(self):
        """It should not Deserialize an Item with a missing field"""
        for field in ("product_id", "name", "quantity", "price"):
            with self.subTest(field=field):
                data = make_item_data()
                del data[field]
                self.assertRaises(DataValidationError, Item().deserialize, data)

    def test_deserialize_item_bad_quantity(self):
        """It should not Deserialize an Item with an invalid quantity"""
        for quantity in (0, -1, 1.5, "2", True, None):
            with self.subTest(quantity=quantity):
                self.assertRaises(
                    DataValidationError,
                    Item().deserialize,
                    make_item_data(quantity=quantity),
                )

    def test_deserialize_item_bad_price(self):
        """It should not Deserialize an Item with an invalid price"""
        bad_prices = (-0.01, "abc", "24.99", True, None)
        not_finite = (float("nan"), float("inf"), float("-inf"), Decimal("NaN"))
        for price in bad_prices + not_finite:
            with self.subTest(price=price):
                self.assertRaises(
                    DataValidationError, Item().deserialize, make_item_data(price=price)
                )

    def test_deserialize_item_bad_product_id(self):
        """It should not Deserialize an Item with a product_id that is not an integer"""
        for product_id in ("1001", 10.5, True):
            with self.subTest(product_id=product_id):
                self.assertRaises(
                    DataValidationError,
                    Item().deserialize,
                    make_item_data(product_id=product_id),
                )

    def test_deserialize_item_bad_name(self):
        """It should not Deserialize an Item with an empty or non-string name"""
        for name in ("", 42):
            with self.subTest(name=name):
                self.assertRaises(
                    DataValidationError, Item().deserialize, make_item_data(name=name)
                )

    def test_deserialize_item_not_a_dict(self):
        """It should not Deserialize an Item from data that is not a dictionary"""
        for data in (None, "item", [1, 2]):
            with self.subTest(data=data):
                self.assertRaises(DataValidationError, Item().deserialize, data)

    def test_item_repr(self):
        """It should have a readable repr"""
        item = ItemFactory(name="Vinyl record")
        self.assertIn("Vinyl record", repr(item))
