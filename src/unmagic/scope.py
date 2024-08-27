"""Pytest scope integration and access to magic fixtures

This module provides access the the active scope node, magic fixture
values, and a function to add scope finalizers.

PYTEST_DONT_REWRITE
"""
from dataclasses import dataclass, field

import pytest
from _pytest.main import Session
from _pytest.fixtures import FixtureRequest

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


def pytest_sessionstart(session):
    """Set active session and requests

    Other plugins may override the active scope state with a context
    sensitive object such as a threading.local, for exapmle:

    def pytest_runtestloop(session):
        from threading import local
        value = local()
        value.__dict__.update(vars(Active(session)))
        set_active(value)
    """
    set_active(Active(session))


def pytest_sessionfinish():
    set_active(None)


def pytest_itemcollected(item):
    fixtures = getattr(item.obj, "unmagic_fixtures", None)
    if fixtures:
        for fixture in fixtures:
            if not fixture._is_registered_for(item):
                fixture._register(item)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_protocol(item):
    active = get_active(item.session)
    active.request = item._request
    yield
    active.request = None


def get_active(session=None):
    if session is not None:
        ss = getattr(_active, "session", None)
        if ss is None:
            raise ValueError("There is no active pytest session")
        elif ss is not session:
            raise ValueError("Found unexpected active pytest session")
    return _active


def set_active(value):
    global _active
    _active = value


@dataclass
class Active:
    session: Session
    request: FixtureRequest = field(default=None)
