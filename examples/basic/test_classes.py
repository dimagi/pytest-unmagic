# examples/basic/test_classes.py
"""Class-based test examples, including unittest.TestCase.

Run: pytest examples/basic/test_classes.py -v
"""
import unittest

from unmagic import fixture, use


@fixture
def items():
    yield []


@use(items)
class TestWithUse:
    """Apply fixture to all methods in a regular test class."""

    def test_add(self):
        cart = items()
        cart.append("apple")
        assert cart == ["apple"]

    def test_empty(self):
        cart = items()
        assert cart == []


@use(items)
class TestWithTestCase(unittest.TestCase):
    """Apply fixture to unittest.TestCase -- not possible with standard pytest."""

    def test_add(self):
        cart = items()
        cart.append("banana")
        self.assertEqual(cart, ["banana"])

    def test_empty(self):
        cart = items()
        self.assertEqual(cart, [])
