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


def get_request(scope="function"):
    """Get the active request

    :param scope: Optional scope. Default "function".
    :raises: ``ValueError`` if there is no active request in scope.
    """
    requests = get_active().requests.get(scope)
    if not requests:
        raise ValueError(f"There is no active {scope}-scoped request")
    return requests[-1]


def get_scope_data():
    """Get scope data from the active session"""
    stash = get_active().session.stash
    value = stash.get(_scope_data_key, None)
    if value is None:
        value = stash[_scope_data_key] = defaultdict(dict)
    return value


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
        value.requests = defaultdict(list)
        set_active(value)
    """
    set_active(Active(session, defaultdict(list)))


def pytest_sessionfinish():
    set_active(None)


def pytest_collection(session):
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
        # ensure scope fixtures are run before other fixtures in the
        # same scope so get_fixture_value() uses the correct request
        _autouse_fixture_try_first(func.__name__, session._fixturemanager)


def _autouse_fixture_try_first(name, fixturemanager):
    names = fixturemanager._nodeid_autousenames['']
    assert names[-1] == name, f"{names}[-1] != {name!r}"
    names.insert(0, names.pop())


def _make_scope_fixture(scope):
    def fixture(request):
        requests = get_active(request.session).requests[scope]
        requests.append(request)
        try:
            yield
        finally:
            assert requests[-1] is request, f"{requests[-1]} is not {request}"
            requests.pop()

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
