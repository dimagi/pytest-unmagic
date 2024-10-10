"""Pytest scope integration and access to magic fixtures

This module provides access the the active scope node, magic fixture
values, and a function to add scope finalizers.

PYTEST_DONT_REWRITE
"""
from dataclasses import dataclass, field

import pytest

from . import _api

_active = None
_previous_active = pytest.StashKey()


def get_request():
    """Get the active request

    :raises: ``ValueError`` if there is no active request.
    """
    request = get_active().request
    if not request:
        raise ValueError("There is no active request")
    return request


def pytest_configure(config):
    if _active is not None:
        config.stash[_previous_active] = _active
    set_active(None)


def pytest_unconfigure(config):
    set_active(config.stash.get(_previous_active, None))


@pytest.hookimpl(trylast=True)
def pytest_sessionstart(session):
    """Set active session

    Other plugins may override the active scope state with a context
    sensitive object such as a ``threading.local``, for exapmle:

        def pytest_runtestloop(session):
            from threading import local
            value = local()
            value.__dict__.update(vars(Active(session)))
            set_active(value)
    """
    from .autouse import _register_early_autouses
    set_active(Active(session))
    _register_early_autouses(session)


def pytest_sessionfinish():
    set_active(None)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_protocol(item):
    active = get_active(item.session)
    active.request = _api.get_request(item)
    yield
    active.request = None


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_fixture_setup(request):
    active = get_active(request.session)
    parent = active.request
    active.request = request
    yield
    active.request = parent


def get_active(session=None):
    """Get object with active pytest session and request"""
    if session is not None:
        ss = getattr(_active, "session", None)
        if ss is None:
            raise ValueError("There is no active pytest session")
        elif ss is not session:
            raise ValueError("Found unexpected active pytest session")
    return _active


def set_active(value):
    """Set object with active pytest session and request"""
    global _active
    _active = value


@dataclass
class Active:
    session: pytest.Session
    request: pytest.FixtureRequest = field(default=None)
