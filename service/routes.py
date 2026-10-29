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
Shopcart Service

This service implements a REST API that allows you to Create, Read, Update
and Delete Shopcart
"""

from flask import jsonify, request, url_for, abort
from flask import current_app as app  # Import Flask application
from service.models import Shopcart, Item
from service.common import status  # HTTP Status Codes


######################################################################
# GET INDEX
######################################################################
@app.route("/")
def index():
    """Root URL response"""
    app.logger.info("Request for Root URL")
    return (
        jsonify(
            name="Shopcart REST API Service",
            version="1.0",
            paths=url_for("list_shopcarts", _external=True),
        ),
        status.HTTP_200_OK,
    )


######################################################################
# HEALTH CHECK
######################################################################
@app.route("/health")
def health():
    """Liveness and readiness check for Kubernetes. Does not touch the database."""
    return jsonify(status="OK"), status.HTTP_200_OK


######################################################################
#  R E S T   A P I   E N D P O I N T S
######################################################################


######################################################################
# READ A SHOPCART
######################################################################
@app.route("/shopcarts/<int:shopcart_id>", methods=["GET"])
def get_shopcarts(shopcart_id):
    """
    Retrieve a single Shopcart

    This endpoint will return a Shopcart and its Items based on its id
    """
    app.logger.info("Request to read a Shopcart with id: %s", shopcart_id)

    shopcart = Shopcart.find(shopcart_id)
    if not shopcart:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Shopcart with id '{shopcart_id}' could not be found.",
        )

    return jsonify(shopcart.serialize()), status.HTTP_200_OK


######################################################################
# UPDATE AN EXISTING SHOPCART
######################################################################
@app.route("/shopcarts/<int:shopcart_id>", methods=["PUT"])
def update_shopcart(shopcart_id):
    """
    Update a Shopcart

    This endpoint will update a Shopcart based on the body that is posted.
    If "items" is sent, it replaces the Items of the Shopcart.
    """
    app.logger.info("Request to update a Shopcart with id: %s", shopcart_id)

    shopcart = Shopcart.find(shopcart_id)
    if not shopcart:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Shopcart with id '{shopcart_id}' could not be found.",
        )

    shopcart.deserialize(request.get_json())
    shopcart.update()

    return jsonify(shopcart.serialize()), status.HTTP_200_OK


######################################################################
# CREATE A SHOPCART
######################################################################
@app.route("/shopcarts", methods=["POST"])
def create_shopcart():
    """Creates a new Shopcart"""
    app.logger.info("Request to create a Shopcart")

    data = request.get_json()
    shopcart = Shopcart()
    shopcart.deserialize(data)
    shopcart.create()

    location_url = url_for("get_shopcarts", shopcart_id=shopcart.id, _external=True)

    return (
        jsonify(shopcart.serialize()),
        status.HTTP_201_CREATED,
        {"Location": location_url},
    )


######################################################################
# DELETE A SHOPCART
######################################################################
@app.route("/shopcarts/<int:shopcart_id>", methods=["DELETE"])
def delete_shopcart(shopcart_id):
    """
    Delete a Shopcart

    This endpoint will delete a Shopcart and its Items based on the id specified in the path.
    DELETE is idempotent, so it returns 204 even if the Shopcart doesn't exist.
    """
    app.logger.info("Request to delete a Shopcart with id: %s", shopcart_id)

    shopcart = Shopcart.find(shopcart_id)
    if shopcart:
        shopcart.delete()
        app.logger.info("Shopcart with id [%s] deleted", shopcart_id)

    return "", status.HTTP_204_NO_CONTENT


######################################################################
# LIST ALL SHOPCARTS
######################################################################
@app.route("/shopcarts", methods=["GET"])
def list_shopcarts():
    """Returns all of the Shopcarts and their Items"""
    app.logger.info("Request to list Shopcarts")

    shopcarts = Shopcart.all()
    results = [shopcart.serialize() for shopcart in shopcarts]
    app.logger.info("Returning %d Shopcarts", len(results))

    return jsonify(results), status.HTTP_200_OK


######################################################################
# ADD AN ITEM
######################################################################
@app.route("/shopcarts/<int:shopcart_id>/items", methods=["POST"])
def add_item(shopcart_id):
    """Add an item to an existing shopcart."""
    app.logger.info("Request to add an item")
    shopcart = Shopcart.find(shopcart_id)
    if shopcart is None:
        app.logger.info("Unable to find shopcart")
        abort(status.HTTP_404_NOT_FOUND, description="Shopcart not found")
    data = request.get_json()
    item = Item()
    item.deserialize(data)
    item.shopcart_id = shopcart_id
    item.create()
    location_url = f"/shopcarts/{shopcart_id}/items/{item.id}"
    return (
        jsonify(item.serialize()),
        status.HTTP_201_CREATED,
        {"Location": location_url},
    )


######################################################################
# UPDATE AN ITEM IN A SHOPCART (#10)
######################################################################
@app.route("/shopcarts/<int:shopcart_id>/items/<int:item_id>", methods=["PUT"])
def update_item(shopcart_id, item_id):
    """Update an existing Item without changing its ID or parent Shopcart.

    PUT requires product_id, name, quantity, and price. Item.deserialize()
    validates the data and ignores id and shopcart_id supplied in the body.
    """
    app.logger.info(
        "Request to update Item %s in Shopcart %s", item_id, shopcart_id
    )

    shopcart = Shopcart.find(shopcart_id)
    if shopcart is None:
        abort(status.HTTP_404_NOT_FOUND, description="Shopcart not found")

    item = Item.find(item_id)
    if item is None or item.shopcart_id != shopcart_id:
        abort(
            status.HTTP_404_NOT_FOUND,
            description="Item not found in this shopcart",
        )

    item.deserialize(request.get_json())
    item.update()

    return jsonify(item.serialize()), status.HTTP_200_OK


######################################################################
# DELETE AN ITEM
######################################################################
@app.route("/shopcarts/<int:shopcart_id>/items/<int:item_id>", methods=["DELETE"])
def delete_item(shopcart_id, item_id):
    """Delete an item from a shopcart.

    DELETE is idempotent, so it returns 204 even if the shopcart or item doesn't
    exist. An item that belongs to a different shopcart is left alone.
    """
    app.logger.info("Request to delete item %s from shopcart %s", item_id, shopcart_id)

    item = Item.find(item_id)
    if item and item.shopcart_id == shopcart_id:
        item.delete()
        app.logger.info("Item with id [%s] deleted", item_id)

    return "", status.HTTP_204_NO_CONTENT


######################################################################
# READ AN ITEM FROM A SHOPCART (#13)
######################################################################
@app.route("/shopcarts/<int:shopcart_id>/items/<int:item_id>", methods=["GET"])
def get_item(shopcart_id, item_id):
    """Read a specific Item from an existing Shopcart."""
    app.logger.info(
        "Request to read Item %s from Shopcart %s",
        item_id,
        shopcart_id,
    )

    shopcart = Shopcart.find(shopcart_id)
    if shopcart is None:
        abort(status.HTTP_404_NOT_FOUND, description="Shopcart not found")

    item = Item.find(item_id)
    if item is None or item.shopcart_id != shopcart_id:
        abort(
            status.HTTP_404_NOT_FOUND,
            description="Item not found in this shopcart",
        )

    return jsonify(item.serialize()), status.HTTP_200_OK


######################################################################
# LIST ITEMS IN A SHOPCART
######################################################################
@app.route("/shopcarts/<int:shopcart_id>/items", methods=["GET"])
def list_items(shopcart_id):
    """Returns all of the Items in a Shopcart"""
    app.logger.info("Request to list Items in Shopcart with id: %s", shopcart_id)

    shopcart = Shopcart.find(shopcart_id)
    if not shopcart:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Shopcart with id '{shopcart_id}' could not be found.",
        )

    results = [item.serialize() for item in shopcart.items]
    app.logger.info("Returning %d Items", len(results))

    return jsonify(results), status.HTTP_200_OK


######################################################################
# CHECKOUT A SHOPCART (ACTION)
######################################################################
@app.route("/shopcarts/<int:shopcart_id>/checkout", methods=["PUT"])
def checkout_shopcart(shopcart_id):
    """
    Checkout a Shopcart

    This action moves a Shopcart to CHECKED_OUT. No request body is needed.
    Checking out an already checked out cart returns it unchanged.
    """
    app.logger.info("Request to checkout Shopcart with id: %s", shopcart_id)

    shopcart = Shopcart.find(shopcart_id)
    if not shopcart:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Shopcart with id '{shopcart_id}' could not be found.",
        )

    shopcart.checkout()

    return jsonify(shopcart.serialize()), status.HTTP_200_OK
