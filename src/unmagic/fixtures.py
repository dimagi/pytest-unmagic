"""Simple unmagical fixture decorators

Unmagic fixtures use standard Python import semantics, making their
origins more intuitive.

PYTEST_DONT_REWRITE
"""
from contextlib import _GeneratorContextManager
from functools import cached_property, wraps
from inspect import isgeneratorfunction, Signature
from os.path import dirname
from unittest import mock

import pytest

from . import _api
from .autouse import autouse as _autouse
from .scope import get_request

__all__ = ["fixture", "use"]


def fixture(func=None, /, scope="function", autouse=False):
    """Unmagic fixture decorator

    The decorated function must `yield` exactly once. The yielded value
    will be the fixture value, and code after the yield is executed at
    teardown. Fixtures may be passed to `@use()` or applied directly as
    a decorator to a test or other fixture.

    This function also accepts context managers and strings as the first
    argument. A string will create a fixture that looks up the
    `pytest.fixture` with that name.

    A fixture can be assigned a scope. It will be setup for the first
    test that uses it and torn down at the end of its scope.

    A fixture can be called without arguments within its scope or
    a lower scope to retrieve the value of the fixture.
    """
    def fixture(func):
        if not isgeneratorfunction(func):
            return UnmagicFixture.create(func, scope, autouse)
        return UnmagicFixture(func, scope, autouse)
    return fixture if func is None else fixture(func)


def use(*fixtures):
    """Apply fixture(s) to a function

    Accepted fixture types:

        - `unmagic.fixture`
        - context manager
        - name of a `pytest.fixture` (`str`)
    """
    if not fixtures:
        raise TypeError("At least one fixture is required")

    def apply_fixtures(func):
        if _api.safe_isclass(func):
            func.__unmagic_fixtures__ = fixtures
            return func

        def setup_fixtures():
            try:
                for setup in unmagics:
                    setup()
            except Exception as exc:
                pytest.fail(f"fixture setup for {func.__name__!r} failed: "
                            f"{type(exc).__name__}: {exc}")

        is_fixture = isinstance(func, UnmagicFixture)
        if is_fixture:
            if func.autouse:
                raise TypeError(
                    f"Cannot apply @use to autouse fixture {func}. "
                    "Hint: apply @use before @fixture(autouse=...)"
                )
            func, scope = func.func, func.scope

        if isgeneratorfunction(func):
            @wraps(func)
            def run_with_fixtures(*args, **kw):
                setup_fixtures()
                yield from func(*args, **kw)
        else:
            @wraps(func)
            def run_with_fixtures(*args, **kw):
                setup_fixtures()
                return func(*args, **kw)

        unmagics = [UnmagicFixture.create(f) for f in fixtures]
        seen = set(unmagics)
        subs = [sub
                for fix in unmagics
                for sub in getattr(fix, "unmagic_fixtures", [])
                if sub not in seen and (seen.add(sub) or True)]
        if hasattr(func, "unmagic_fixtures"):
            subs.extend(f for f in func.unmagic_fixtures if f not in seen)
        run_with_fixtures.unmagic_fixtures = subs + unmagics

        if is_fixture:
            return fixture(run_with_fixtures, scope=scope)
        return run_with_fixtures
    return apply_fixtures


class UnmagicFixture:
    _pytestfixturefunction = ...  # prevent pytest running fixture as test

    @classmethod
    def create(cls, fixture, scope="function", autouse=False):
        if isinstance(fixture, cls):
            return fixture
        if isinstance(fixture, str):
            return PytestFixture(fixture, scope, autouse)

        outer = fixture
        if (
            callable(fixture)
            and not hasattr(type(fixture), "__enter__")
            and not hasattr(fixture, "unmagic_fixtures")
        ):
            fixture = fixture()
        if not hasattr(type(fixture), "__enter__"):
            raise TypeError(
                f"{outer!r} is not a fixture. Hint: expected generator "
                "functcion, context manager, or pytest.fixture name."
            )
        if isinstance(fixture, _GeneratorContextManager):
            # special case for contextmanager
            inner = wrapped = fixture.func
        else:
            if isinstance(fixture, mock._patch):
                inner = _pretty_patch(fixture)
            else:
                inner = type(fixture)
            wrapped = inner.__enter__  # must be a function

        @wraps(inner)
        def func():
            with fixture as value:
                yield value
        func.__unmagic_wrapped__ = outer
        func.__wrapped__ = wrapped
        # prevent pytest from introspecting arguments from wrapped function
        func.__signature__ = Signature()
        return cls(func, scope, autouse)

    def __init__(self, func, scope, autouse):
        self.func = func
        self.scope = scope
        self.autouse = autouse
        if autouse:
            _autouse(self, autouse)

    @cached_property
    def _id(self):
        return _UnmagicID(self.__name__)

    @property
    def unmagic_fixtures(self):
        return self.func.unmagic_fixtures

    @property
    def __name__(self):
        return self.func.__name__

    @property
    def __doc__(self):
        return self.func.__doc__

    @property
    def __module__(self):
        return self.func.__module__

    def __repr__(self):
        return f"<{type(self).__name__} {self.__name__} {hex(hash(self))}>"

    def __call__(self, function=None):
        if function is None:
            return self._get_value()
        return use(self)(function)

    def _get_value(self):
        request = get_request()
        if not self._is_registered_for(request.node):
            self._register(request.node)
        return request.getfixturevalue(self._id)

    def _is_registered_for(self, node):
        return _api.getfixturedefs(node, self._id)

    def _register(self, node):
        if self.autouse is True:
            scope_node_id = ""
        else:
            scope_node_id = _SCOPE_NODE_ID[self.scope](node.nodeid)
        assert isgeneratorfunction(self.func), repr(self)
        _api.register_fixture(
            node.session,
            name=self._id,
            func=self.func,
            nodeid=scope_node_id,
            scope=self.scope,
            autouse=self.autouse,
        )


class PytestFixture(UnmagicFixture):

    def __init__(self, name, scope, autouse):
        if autouse:
            raise ValueError(f"Cannot autouse pytest.fixture: {name!r}")
        if scope != "function":
            raise ValueError(f"Cannot set scope of pytest.fixture: {name!r}")

        def func():
            assert 0, "should not get here"
        func.__name__ = self._id = name
        func.__doc__ = f"Unmagic-wrapped pytest.fixture: {name!r}"
        super().__init__(func, None, None)

    def _get_value(self):
        return get_request().getfixturevalue(self._id)

    def _is_registered_for(self, node):
        return True

    def _register(self, node):
        raise NotImplementedError


_SCOPE_NODE_ID = {
    "function": lambda n: n,
    "class": lambda n: n.rsplit("::", 1)[0],
    "module": lambda n: n.split("::", 1)[0],
    "package": lambda n: dirname(n.split("::", 1)[0]),
    "session": lambda n: "",
}


class _UnmagicID(str):
    __slots__ = ()

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    def __hash__(self):
        return id(self)

    def __repr__(self):
        return f"<{self} {hex(hash(self))}>"


def _pretty_patch(patch):
    @wraps(type(patch))
    def func():
        pass
    target = patch.getter()
    src = getattr(target, "__name__", repr(target))
    func.__name__ = f"<patch {src}.{patch.attribute}>"
    return func


def pytest_pycollect_makeitem(collector, name, obj):
    # apply class fixtures to test methods
    if _api.safe_isclass(obj) and collector.istestclass(obj, name):
        unmagic_fixtures = getattr(obj, "__unmagic_fixtures__", None)
        if unmagic_fixtures:
            for key in dir(obj):
                val = _api.safe_getattr(obj, key, None)
                if (
                    not _api.safe_isclass(val)
                    and collector.istestfunction(val, key)
                ):
                    setattr(obj, key, use(*unmagic_fixtures)(val))


def pytest_itemcollected(item):
    # register fixtures
    fixtures = getattr(item.obj, "unmagic_fixtures", None)
    if fixtures:
        for fixture in fixtures:
            if not fixture._is_registered_for(item):
                fixture._register(item)
