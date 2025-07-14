"""Pytest fixtures with conventional import semantics

The primary motivation of this project is to remove the argument-name-
matching magic in pytest fixtures.
"""
from .autouse import autouse
from .fixtures import fixture, use
from .scope import get_request

__version__ = "1.0.1"
__all__ = ["autouse", "fixture", "get_request", "use"]

pytest_plugins = ["unmagic.fence", "unmagic.fixtures", "unmagic.scope"]
