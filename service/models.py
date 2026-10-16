"""
Models for Shopcart and Item

All of the models are stored in this module
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger("flask.app")

# Create the SQLAlchemy object to be initialized later in init_db()
db = SQLAlchemy()


class DataValidationError(Exception):
    """Used for an data validation errors when deserializing"""


def utc_now():
    """Returns the current time in UTC"""
    return datetime.now(timezone.utc)


def is_int(value):
    """Returns True if value is an int (bool is not accepted)"""
    return isinstance(value, int) and not isinstance(value, bool)


######################################################################
#  P E R S I S T E N T   B A S E   M O D E L
######################################################################
class PersistentBase:
    """Base class that adds persistent methods to the models"""

    def create(self):
        """
        Creates the record in the database
        """
        logger.info("Creating %s", self)
        # id must be none to generate next primary key
        self.id = None  # pylint: disable=invalid-name, attribute-defined-outside-init
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error creating record: %s", self)
            raise DataValidationError(e) from e

    def update(self):
        """
        Updates the record in the database
        """
        # reading an expired id must not flush bad data outside the try below
        with db.session.no_autoflush:
            if not self.id:
                raise DataValidationError("Update called with empty ID field")
            logger.info("Updating %s", self)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error updating record: %s", self)
            raise DataValidationError(e) from e

    def delete(self):
        """Removes the record from the data store"""
        logger.info("Deleting %s", self)
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error deleting record: %s", self)
            raise DataValidationError(e) from e

    @classmethod
    def all(cls):
        """Returns all of the records in the database"""
        logger.info("Processing all %s records", cls.__name__)
        return cls.query.all()

    @classmethod
    def find(cls, by_id):
        """Finds a record by it's ID"""
        logger.info("Processing %s lookup for id %s ...", cls.__name__, by_id)
        return cls.query.session.get(cls, by_id)


######################################################################
#  I T E M   M O D E L
######################################################################
class Item(db.Model, PersistentBase):
    """
    Class that represents an Item in a Shopcart
    """

    ##################################################
    # Table Schema
    ##################################################
    id = db.Column(db.Integer, primary_key=True)
    shopcart_id = db.Column(
        db.Integer, db.ForeignKey("shopcart.id", ondelete="CASCADE"), nullable=False
    )
    product_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    # The database also rejects bad values, not just deserialize()
    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="item_quantity_positive"),
        db.CheckConstraint("price >= 0", name="item_price_not_negative"),
    )

    def __repr__(self):
        return f"<Item {self.name} id=[{self.id}] shopcart[{self.shopcart_id}]>"

    def serialize(self):
        """Serializes an Item into a dictionary"""
        return {
            "id": self.id,
            "shopcart_id": self.shopcart_id,
            "product_id": self.product_id,
            "name": self.name,
            "quantity": self.quantity,
            "price": float(self.price),
        }

    def deserialize(self, data):
        """
        Deserializes an Item from a dictionary

        id and shopcart_id are ignored: the Shopcart or the URL sets the
        shopcart_id, and an Item can not be moved to another Shopcart.

        Args:
            data (dict): A dictionary containing the resource data
        """
        if not isinstance(data, dict):
            raise DataValidationError(
                "Invalid Item: body of request contained bad or no data"
            )
        try:
            product_id = data["product_id"]
            name = data["name"]
            quantity = data["quantity"]
            price = data["price"]
        except KeyError as error:
            raise DataValidationError(
                "Invalid Item: missing " + error.args[0]
            ) from error

        if not is_int(product_id):
            raise DataValidationError("Invalid Item: product_id must be an integer")
        if not isinstance(name, str) or not name:
            raise DataValidationError("Invalid Item: name must be a non-empty string")
        if not is_int(quantity) or quantity <= 0:
            raise DataValidationError(
                "Invalid Item: quantity must be a positive integer"
            )
        if isinstance(price, bool) or not isinstance(price, (int, float, Decimal)):
            raise DataValidationError(
                "Invalid Item: price must be a non-negative number"
            )
        price = Decimal(str(price))
        # JSON allows NaN and Infinity, which are not valid prices
        if not price.is_finite() or price < 0:
            raise DataValidationError(
                "Invalid Item: price must be a non-negative number"
            )

        self.product_id = product_id
        self.name = name
        self.quantity = quantity
        self.price = price
        return self


######################################################################
#  S H O P C A R T   M O D E L
######################################################################
class Shopcart(db.Model, PersistentBase):
    """
    Class that represents a Shopcart
    """

    ##################################################
    # Table Schema
    ##################################################
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    last_updated = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    items = db.relationship(
        "Item",
        backref="shopcart",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Item.id",
    )

    def __repr__(self):
        return f"<Shopcart id=[{self.id}] user_id={self.user_id}>"

    def update(self):
        """
        Updates the Shopcart in the database

        onupdate only fires when a Shopcart column changes, so last_updated
        is set here to also cover changes to the Items alone.
        """
        self.last_updated = utc_now()
        super().update()

    def serialize(self):
        """Serializes a Shopcart and its Items into a dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
            "items": [item.serialize() for item in self.items],
        }

    def deserialize(self, data):
        """
        Deserializes a Shopcart and its Items from a dictionary

        id, created_at and last_updated are managed by the server and are ignored.
        If "items" is sent, it replaces the current Items. Nothing is changed
        unless every Item is valid.

        Args:
            data (dict): A dictionary containing the resource data
        """
        if not isinstance(data, dict):
            raise DataValidationError(
                "Invalid Shopcart: body of request contained bad or no data"
            )
        try:
            user_id = data["user_id"]
        except KeyError as error:
            raise DataValidationError(
                "Invalid Shopcart: missing " + error.args[0]
            ) from error
        if not is_int(user_id):
            raise DataValidationError("Invalid Shopcart: user_id must be an integer")

        items = None
        if "items" in data:
            if not isinstance(data["items"], list):
                raise DataValidationError("Invalid Shopcart: items must be a list")
            # build every Item first so a bad one leaves the Shopcart untouched
            items = [Item().deserialize(item_data) for item_data in data["items"]]

        self.user_id = user_id
        if items is not None:
            self.items = items
        return self
