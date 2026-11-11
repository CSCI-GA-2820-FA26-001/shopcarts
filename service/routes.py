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
from flask_restx import Api, Resource, fields
from service.models import Shopcart, Item, SHOPCART_STATUSES, is_database_integer
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
            paths=url_for("shopcart_collection", _external=True),
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
# Configure Swagger before initializing it
######################################################################
api = Api(
    app,
    version="1.0.0",
    title="Shopcart REST API Service",
    description="This is the Shopcarts service of the NYU DevOps eCommerce project.",
    default="shopcarts",
    default_label="Shopcart operations",
    doc="/apidocs/",
    prefix="/api",
)

# Define the models so that the docs reflect what can be sent
item_create_model = api.model(
    "ItemCreate",
    {
        "product_id": fields.Integer(required=True, description="The product identifier"),
        "name": fields.String(required=True, description="The name of the product"),
        "quantity": fields.Integer(required=True, description="The number of units (> 0)"),
        "price": fields.Float(required=True, description="The unit price (>= 0)"),
    },
)

item_model = api.clone(
    "Item",
    item_create_model,
    {
        "id": fields.Integer(readonly=True, description="The unique id assigned internally by service"),
        "shopcart_id": fields.Integer(readonly=True, description="The id of the Shopcart the Item belongs to"),
    },
)

create_model = api.model(
    "ShopcartCreate",
    {
        "user_id": fields.Integer(required=True, description="The id of the customer the Shopcart belongs to"),
        "items": fields.List(
            fields.Nested(item_create_model),
            description="The Items of the Shopcart. On update, replaces the current Items if sent",
        ),
    },
)

shopcart_model = api.clone(
    "Shopcart",
    create_model,
    {
        "id": fields.Integer(readonly=True, description="The unique id assigned internally by service"),
        "status": fields.String(
            readonly=True,
            enum=list(SHOPCART_STATUSES),
            description="OPEN until the Shopcart is checked out. Set by the service only",
        ),
        "created_at": fields.DateTime(readonly=True, description="When the Shopcart was created"),
        "last_updated": fields.DateTime(readonly=True, description="When the Shopcart or its Items last changed"),
        "items": fields.List(fields.Nested(item_model), description="The Items of the Shopcart"),
    },
)


######################################################################
#  R E S T   A P I   E N D P O I N T S
######################################################################


######################################################################
#  PATH: /shopcarts/{id}
######################################################################
@api.route("/shopcarts/<int:shopcart_id>")
@api.param("shopcart_id", "The Shopcart identifier")
class ShopcartResource(Resource):
    """
    ShopcartResource class

    Allows the manipulation of a single Shopcart
    GET /shopcarts/{id} - Returns a Shopcart with the id
    PUT /shopcarts/{id} - Update a Shopcart with the id
    DELETE /shopcarts/{id} - Deletes a Shopcart with the id
    """

    # ------------------------------------------------------------------
    # RETRIEVE A SHOPCART
    # ------------------------------------------------------------------
    @api.doc("get_shopcart")
    @api.response(404, "Shopcart not found")
    @api.marshal_with(shopcart_model)
    def get(self, shopcart_id):
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

        return shopcart.serialize(), status.HTTP_200_OK

    # ------------------------------------------------------------------
    # UPDATE AN EXISTING SHOPCART
    # ------------------------------------------------------------------
    @api.doc("update_shopcart")
    @api.response(404, "Shopcart not found")
    @api.response(400, "The posted Shopcart data was not valid")
    @api.response(415, "The request was not JSON")
    @api.expect(create_model)
    @api.marshal_with(shopcart_model)
    def put(self, shopcart_id):
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

        return shopcart.serialize(), status.HTTP_200_OK

    # ------------------------------------------------------------------
    # DELETE A SHOPCART
    # ------------------------------------------------------------------
    @api.doc("delete_shopcart")
    @api.response(204, "Shopcart deleted")
    def delete(self, shopcart_id):
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
#  PATH: /shopcarts
######################################################################
@api.route("/shopcarts", strict_slashes=False)
class ShopcartCollection(Resource):
    """Handles all interactions with collections of Shopcarts"""

    # ------------------------------------------------------------------
    # LIST ALL SHOPCARTS
    # ------------------------------------------------------------------
    @api.doc("list_shopcarts")
    @api.response(400, "user_id was not an integer")
    @api.marshal_list_with(shopcart_model)
    def get(self):
        """
        Returns all of the Shopcarts and their Items

        ?user_id=<int> returns only the Shopcarts of that user.
        """
        app.logger.info("Request to list Shopcarts")

        user_id = request.args.get("user_id")
        if user_id is None:
            shopcarts = Shopcart.all()
        else:
            try:
                user_id = int(user_id)
            except ValueError:
                abort(status.HTTP_400_BAD_REQUEST, "user_id must be an integer")

            if not is_database_integer(user_id):
                abort(
                    status.HTTP_400_BAD_REQUEST,
                    "user_id exceeds database integer range",
                )

            shopcarts = Shopcart.find_by_user_id(user_id)

        results = [shopcart.serialize() for shopcart in shopcarts]
        app.logger.info("Returning %d Shopcarts", len(results))

        return results, status.HTTP_200_OK

    # ------------------------------------------------------------------
    # CREATE A SHOPCART
    # ------------------------------------------------------------------
    @api.doc("create_shopcart")
    @api.response(400, "The posted Shopcart data was not valid")
    @api.response(415, "The request was not JSON")
    @api.expect(create_model)
    @api.marshal_with(shopcart_model, code=201)
    def post(self):
        """Creates a new Shopcart"""
        app.logger.info("Request to create a Shopcart")

        data = request.get_json()
        shopcart = Shopcart()
        shopcart.deserialize(data)
        shopcart.create()

        location_url = api.url_for(ShopcartResource, shopcart_id=shopcart.id, _external=True)

        return shopcart.serialize(), status.HTTP_201_CREATED, {"Location": location_url}


######################################################################
#  PATH: /shopcarts/{shopcart_id}/items/{item_id}
######################################################################
@api.route("/shopcarts/<int:shopcart_id>/items/<int:item_id>")
@api.param("shopcart_id", "The Shopcart identifier")
@api.param("item_id", "The Item identifier")
class ItemResource(Resource):
    """
    ItemResource class

    Allows the manipulation of a single Item in a Shopcart
    GET /shopcarts/{shopcart_id}/items/{item_id} - Returns the Item
    PUT /shopcarts/{shopcart_id}/items/{item_id} - Updates the Item
    DELETE /shopcarts/{shopcart_id}/items/{item_id} - Deletes the Item
    """

    # ------------------------------------------------------------------
    # READ AN ITEM FROM A SHOPCART
    # ------------------------------------------------------------------
    @api.doc("get_item")
    @api.response(404, "Shopcart or Item not found")
    @api.marshal_with(item_model)
    def get(self, shopcart_id, item_id):
        """
        Retrieve a single Item

        This endpoint will return an Item of the Shopcart based on its id
        """
        app.logger.info("Request to read Item %s from Shopcart %s", item_id, shopcart_id)

        item = find_item_or_404(shopcart_id, item_id)

        return item.serialize(), status.HTTP_200_OK

    # ------------------------------------------------------------------
    # UPDATE AN ITEM IN A SHOPCART
    # ------------------------------------------------------------------
    @api.doc("update_item")
    @api.response(404, "Shopcart or Item not found")
    @api.response(400, "The posted Item data was not valid")
    @api.response(415, "The request was not JSON")
    @api.expect(item_create_model)
    @api.marshal_with(item_model)
    def put(self, shopcart_id, item_id):
        """
        Update an Item

        This endpoint will update an Item without changing its id or its Shopcart.
        product_id, name, quantity and price are all required.
        """
        app.logger.info("Request to update Item %s in Shopcart %s", item_id, shopcart_id)

        item = find_item_or_404(shopcart_id, item_id)
        item.deserialize(request.get_json())
        item.update()

        return item.serialize(), status.HTTP_200_OK

    # ------------------------------------------------------------------
    # DELETE AN ITEM
    # ------------------------------------------------------------------
    @api.doc("delete_item")
    @api.response(204, "Item deleted")
    def delete(self, shopcart_id, item_id):
        """
        Delete an Item

        This endpoint will delete an Item from a Shopcart. DELETE is idempotent, so it
        returns 204 even if the Shopcart or Item doesn't exist. An Item that belongs to
        a different Shopcart is left alone.
        """
        app.logger.info("Request to delete Item %s from Shopcart %s", item_id, shopcart_id)

        item = Item.find(item_id)
        if item and item.shopcart_id == shopcart_id:
            item.delete()
            app.logger.info("Item with id [%s] deleted", item_id)

        return "", status.HTTP_204_NO_CONTENT


######################################################################
#  PATH: /shopcarts/{shopcart_id}/items
######################################################################
@api.route("/shopcarts/<int:shopcart_id>/items", strict_slashes=False)
@api.param("shopcart_id", "The Shopcart identifier")
class ItemCollection(Resource):
    """Handles all interactions with the Items of a Shopcart"""

    # ------------------------------------------------------------------
    # LIST ITEMS IN A SHOPCART
    # ------------------------------------------------------------------
    @api.doc("list_items")
    @api.response(404, "Shopcart not found")
    @api.marshal_list_with(item_model)
    def get(self, shopcart_id):
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

        return results, status.HTTP_200_OK

    # ------------------------------------------------------------------
    # ADD AN ITEM
    # ------------------------------------------------------------------
    @api.doc("create_item")
    @api.response(404, "Shopcart not found")
    @api.response(400, "The posted Item data was not valid")
    @api.response(415, "The request was not JSON")
    @api.expect(item_create_model)
    @api.marshal_with(item_model, code=201)
    def post(self, shopcart_id):
        """
        Add an Item to a Shopcart

        The Item always goes in the Shopcart from the URL. id and shopcart_id in the body are ignored.
        """
        app.logger.info("Request to add an Item to Shopcart %s", shopcart_id)

        shopcart = Shopcart.find(shopcart_id)
        if shopcart is None:
            abort(status.HTTP_404_NOT_FOUND, "Shopcart not found")

        item = Item()
        item.deserialize(request.get_json())
        item.shopcart_id = shopcart_id
        item.create()

        location_url = api.url_for(ItemResource, shopcart_id=shopcart_id, item_id=item.id, _external=True)

        return item.serialize(), status.HTTP_201_CREATED, {"Location": location_url}


######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################


def find_item_or_404(shopcart_id, item_id):
    """Returns the Item of the Shopcart, or aborts with 404 if either doesn't exist"""
    shopcart = Shopcart.find(shopcart_id)
    if shopcart is None:
        abort(status.HTTP_404_NOT_FOUND, "Shopcart not found")

    item = Item.find(item_id)
    if item is None or item.shopcart_id != shopcart_id:
        abort(status.HTTP_404_NOT_FOUND, "Item not found in this shopcart")

    return item


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
