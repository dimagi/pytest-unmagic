"""Simple unmagical fixture decorators

Unmagic fixtures use standard Python import semantics, making their
origins more intuitive.

PYTEST_DONT_REWRITE
"""
from contextlib import _GeneratorContextManager
from functools import cached_property, wraps
from inspect import Parameter, ismethod, signature
from os.path import dirname
from types import GeneratorType
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

    A fixture can be assigned a scope. It will be setup for the first
    test that uses it and torn down at the end of its scope.

    A fixture can be called without arguments within its scope or
    a lower scope to retrieve the value of the fixture.
    """
    def fixture(func):
        return UnmagicFixture(func, scope, autouse)
    return fixture if func is None else fixture(func)


def use(*fixtures):
    """Apply fixture(s) to a function

    Fixtures are passed to the function as positional arguments in the
    same order as they were passed to this decorator factory. Additional
    arguments passed to decorated functions are applied after fixtures.
    Fixture values that do not have a corresponding positional argument
    will not be passed to the decorated function.

    Any context manager may be used as a fixture.

    Magic fixtures may be passed to this decorator. Fixture resolution
    is done using the ``__name__`` attribute of the magic fixture
    function, so the actual fixture that is invoked will follow normal
    pytest fixture resolution rules, which looks first in the test
    module, then in relevant conftest modules, etc. This means that the
    fixture that is resolved may be an override of or even unrelated to
    the one that was passed to ``@use(...)``. In the future this may
    change to use precisely the passed fixture, so it is safest to pass
    the most specific fixture possible (the override rather than the
    overridden fixture).
    """
    if not fixtures:
        raise TypeError("At least one fixture is required")

    def apply_fixtures(func):
        if _api.safe_isclass(func):
            func.__unmagic_fixtures__ = fixtures
            return func

        def get_args(args):
            try:
                fixture_args = [f() for f in unmagics]
                if args and ismethod(getattr(get_request(), "function", None)):
                    # retain self as first argument
                    fixture_args.insert(0, args[0])
                    args = args[1:]
                if len(fixture_args) > num_params:
                    fixture_args = fixture_args[:num_params]
            except Exception as exc:
                pytest.fail(f"fixture setup for {func.__name__!r} failed: "
                            f"{type(exc).__name__}: {exc}")
            return fixture_args, args

        if _api.is_generator(func):
            @wraps(func)
            def run_with_fixtures(*args, **kw):
                fixture_args, args = get_args(args)
                yield from func(*fixture_args, *args, **kw)
        else:
            @wraps(func)
            def run_with_fixtures(*args, **kw):
                fixture_args, args = get_args(args)
                return func(*fixture_args, *args, **kw)

        unmagics = [UnmagicFixture.create(f) for f in fixtures]
        seen = set(unmagics)
        subs = [sub
                for fix in unmagics
                for sub in getattr(fix, "unmagic_fixtures", [])
                if sub not in seen and (seen.add(sub) or True)]
        if hasattr(func, "unmagic_fixtures"):
            subs.extend(f for f in func.unmagic_fixtures if f not in seen)
        run_with_fixtures.unmagic_fixtures = subs + unmagics

        # TODO test possible off-by-one error with "self" method parameter
        sig = signature(func)
        new_params = list(sig.parameters.values())[len(unmagics):]
        num_params = sum(_N_PARAMS(p.kind, 0) for p in sig.parameters.values())
        run_with_fixtures.__signature__ = sig.replace(parameters=new_params)
        if isinstance(func, UnmagicFixture):
            func, scope = func.func, func.scope
            return fixture(run_with_fixtures, scope=scope)
        return run_with_fixtures
    return apply_fixtures


_N_PARAMS = {
    Parameter.POSITIONAL_ONLY: 1,
    Parameter.POSITIONAL_OR_KEYWORD: 1,
}.get


class UnmagicFixture:
    _pytestfixturefunction = ...  # prevent pytest running fixture as test

    @classmethod
    def create(cls, fixture, scope="function"):
        if isinstance(fixture, cls):
            return fixture
        if _api.getfixturemarker(fixture) is not None:
            @wraps(_api.get_real_func(fixture))
            def func():
                yield get_request().getfixturevalue(fixture.__name__)
            func.__pytest_wrapped__ = fixture.__pytest_wrapped__
            func.__unmagic_wrapped__ = fixture
        else:
            outer = fixture
            if callable(fixture) and not hasattr(type(fixture), "__enter__"):
                fixture = fixture()
            if not hasattr(type(fixture), "__enter__"):
                raise ValueError(f"{fixture!r} is not a fixture")
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
            func.__pytest_wrapped__ = _api.Wrapper(wrapped)
            func.__unmagic_wrapped__ = outer
        # delete __wrapped__ to prevent pytest from
        # introspecting arguments from wrapped function
        del func.__wrapped__
        return cls(func, scope, autouse=False)

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
        return getattr(self.func, "unmagic_fixtures")

    @property
    def __pytest_wrapped__(self):
        wrapped = getattr(self.func, "__pytest_wrapped__", None)
        return _api.Wrapper(self.func) if wrapped is None else wrapped

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
        _api.register_fixture(
            node.session,
            name=self._id,
            func=self.get_generator(),
            nodeid=scope_node_id,
            scope=self.scope,
            autouse=self.autouse,
        )

    def get_generator(self):
        if _api.is_generator(self.func):
            return self.func
        return _yield_from(self.func)


_SCOPE_NODE_ID = {
    "function": lambda n: n,
    "class": lambda n: n.rsplit("::", 1)[0],
    "module": lambda n: n.split("::", 1)[0],
    "package": lambda n: dirname(n.split("::", 1)[0]),
    "session": lambda n: "",
}


@fixture
def pytest_request():
    """A fixture that returns the test request"""
    yield get_request()


def _yield_from(func):
    @wraps(func)
    def fixture_generator(*args, **kw):
        gen = func(*args, **kw)
        if not isinstance(gen, GeneratorType):
            raise TypeError(f"fixture {func.__name__!r} does not yield")
        yield from gen
    return fixture_generator


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
