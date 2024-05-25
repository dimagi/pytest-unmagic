"""Reduce pytest magic

The primary motivation of this project is to remove the argument-name-
matching magic in pytest fixtures.
"""
from .fixtures import fixture, get_fixture_value, use

__version__ = "1.0.0"
__all__ = ["fixture", "get_fixture_value", "use"]
