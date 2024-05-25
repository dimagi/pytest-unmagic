"""Pytest scope integration and access to magic fixtures

This module provides access the the active scope node, magic fixture
values, and a function to add scope finalizers.

PYTEST_DONT_REWRITE
"""
from collections import defaultdict, namedtuple
from functools import wraps

import pytest

_active = None
_previous_active = pytest.StashKey()
_scope_data_key = pytest.StashKey()
_addfinalizers_key = pytest.StashKey()


def get_scope_data():
    """Get scope data for the current thread"""
    stash = get_active().session.stash
    value = stash.get(_scope_data_key, None)
    if value is None:
        value = stash[_scope_data_key] = defaultdict(dict)
    return value


def get_addfinalizer(scope):
    """Get a functcion that adds a scope finalizer"""
    return get_active().session.stash[_addfinalizers_key][scope]


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
        value.session = session
        value.requests = []
        set_active(value)
    """
    set_active(Active(session, []))


def pytest_sessionfinish():
    set_active(None)


def pytest_collection(session):
    session.stash[_addfinalizers_key] = addfinalizers = {}
    for func in [
        _make_scope_fixture("function"),
        _skip_if_cls_is_none(_make_scope_fixture("class")),
        _make_scope_fixture("module"),
        _make_scope_fixture("session"),
    ]:
        scope = func.scope
        session._fixturemanager._register_fixture(
            name=func.__name__,
            func=func,
            nodeid=None,
            scope=scope,
            autouse=True,
        )
        addfinalizers[scope] = _get_addfinalizer(session, func.__name__, scope)


def _make_scope_fixture(scope):
    def fixture(request):
        active = get_active(request.session)
        active.requests.append(request)
        try:
            yield
        finally:
            req = active.requests[-1]
            assert req is request, f"{req} is not {request}"
            active.requests.pop()

    fixture.scope = scope
    fixture.__name__ = f"unmagic_{scope}_scope"
    return fixture


def _skip_if_cls_is_none(class_fixture):
    @wraps(class_fixture)
    def fixture(request):
        if request.node.cls is None:
            yield
        else:
            yield from class_fixture(request)
    return fixture


def _get_addfinalizer(session, name, scope):
    faclist = session._fixturemanager._arg2fixturedefs[name]
    fixturedef = faclist[-1]
    assert fixturedef.scope == scope, f"{fixturedef.scope} != {scope}"
    return fixturedef.addfinalizer


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


Active = namedtuple("Active", ["session", "requests"])
