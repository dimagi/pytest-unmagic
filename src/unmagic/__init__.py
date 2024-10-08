"""Reduce pytest magic

The primary motivation of this project is to remove the argument-name-
matching magic in pytest fixtures.
"""
from .autouse import autouse
from .fixtures import fixture, pytest_request, get_fixture_value, use

__version__ = "1.0.0"
__all__ = ["autouse", "fixture", "get_fixture_value", "pytest_request", "use"]

pytest_plugins = ["unmagic.fence", "unmagic.scope"]
