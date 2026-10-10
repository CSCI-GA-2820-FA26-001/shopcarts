"""
Test Factory to make fake objects for testing
"""

from factory import Factory, SubFactory, Sequence, Faker, post_generation
from factory.fuzzy import FuzzyInteger, FuzzyDecimal
from service.models import Shopcart, Item


class ShopcartFactory(Factory):
    """Creates fake Shopcarts"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Maps factory to data model"""

        model = Shopcart

    id = Sequence(lambda n: n)
    user_id = Sequence(lambda n: n + 1)

    @post_generation
    def items(
        self, create, extracted, **kwargs
    ):  # pylint: disable=method-hidden, unused-argument
        """Creates the items list"""
        if not create:
            return

        if extracted:
            self.items = extracted


class ItemFactory(Factory):
    """Creates fake Items"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Maps factory to data model"""

        model = Item

    id = Sequence(lambda n: n)
    shopcart_id = None
    product_id = Sequence(lambda n: 1000 + n)
    name = Faker("word")
    quantity = FuzzyInteger(1, 10)
    price = FuzzyDecimal(0.5, 100.0, 2)
    shopcart = SubFactory(ShopcartFactory)
