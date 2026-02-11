# examples/basic/fixtures.py
"""Shared fixtures for basic examples."""
from unmagic import fixture


@fixture
def greeting():
    """A simple fixture that yields a string value."""
    yield "hello"


@fixture
def items():
    """A fixture that yields a fresh list for each test."""
    yield []


@fixture(scope="module")
def database():
    """A module-scoped fixture simulating a database connection."""
    db = {"connected": True, "data": {}}
    yield db
    db["connected"] = False
    db["data"].clear()
