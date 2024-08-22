"""Simple unmagical fixture decorators

Unmagic fixtures use standard Python import semantics, making their
origins more intuitive.
"""
from functools import cached_property, wraps
from inspect import Parameter, ismethod, signature
from types import GeneratorType

import pytest
from _pytest.compat import is_generator
from _pytest.fixtures import getfixturemarker

from .scope import get_active, get_request

__all__ = ["fixture", "use"]


def fixture(func=None, /, scope="function"):
    """Unmagic fixture decorator

    The decorated function must `yield` exactly once. The yielded value
    will be the fixture value, and code after the yield is executed at
    teardown. Fixtures may be passed to `@use()` or applied directly as
    a decorator to a test or other fixture.

    A fixture can be assigned a scope. It will be setup for the first
    test that uses it and torn down at the end of its scope.

    The fixture's `get_value()` function can be used within its scope or
    a lower scope to setup and retrieve the value of the fixture.
    """
    def fixture(func):
        return UnmagicFixture(func, scope)
    return fixture if func is None else fixture(func)


def get_fixture_value(name):
    """Get magic fixture value

    The fixture will be set up if necessary, and will be torn down
    at the end of its scope.

    The 'unmagic' plugin must be active for this to work.
    """
    if not isinstance(name, str):
        raise ValueError("magic fixture name must be a string")
    return get_request().getfixturevalue(name)


def use(*fixtures):
    """Apply fixture(s) to a function

    Fixtures are passed to the function as positional arguments in the
    same order as they were passed to this decorator factory. Additional
    arguments passed to decorated functions are applied after fixtures.
    Fixture values that do not have a corresponding positional argument
    will not be passed to the decorated function.

    Any context manager may be used as a fixture.
    """
    if not fixtures:
        raise TypeError("At least one fixture is required")

    def apply_fixtures(func):
        @wraps(func)
        def run_with_fixtures(*args, **kw):
            try:
                fixture_args = [_get_value(f, scope) for f in fixtures]
                requests = get_active().requests.get("function")
                if args and requests and ismethod(requests[-1].function):
                    # retain self as first argument
                    fixture_args.insert(0, args[0])
                    args = args[1:]
                if len(fixture_args) > num_params:
                    fixture_args = fixture_args[:num_params]
            except Exception as exc:
                pytest.fail(f"fixture setup for {func.__name__!r} failed: "
                            f"{type(exc).__name__}: {exc}")
            return func(*fixture_args, *args, **kw)

        run_with_fixtures.unmagic_fixtures = fixtures
        sig = signature(func)
        new_params = list(sig.parameters.values())[len(fixtures):]
        num_params = sum(_N_PARAMS(p.kind, 0) for p in sig.parameters.values())
        run_with_fixtures.__signature__ = sig.replace(parameters=new_params)
        if isinstance(func, UnmagicFixture):
            func, scope = func.func, func.scope
            return fixture(run_with_fixtures, scope=scope)
        scope = "function"
        return run_with_fixtures
    return apply_fixtures


_N_PARAMS = {
    Parameter.POSITIONAL_ONLY: 1,
    Parameter.POSITIONAL_OR_KEYWORD: 1,
}.get


class UnmagicFixture:
    __test__ = False

    def __init__(self, func, scope, kw=None):
        self.scope = scope
        self.func = func
        self.kw = kw

    def get_request(self):
        return get_request(self.scope)

    def get_value(self):
        request = self.get_request()
        if self._id not in request._arg2fixturedefs:
            self._register(request)
        return request.getfixturevalue(self._id)

    @cached_property
    def _id(self):
        return repr(self)

    @property
    def __name__(self):
        return self.func.__name__

    def __repr__(self):
        return f"<{type(self).__name__} {self.__name__} {hex(hash(self))}>"

    def __call__(self, function=None, /, **kw):
        if function is None:
            assert not self.kw, f"{self} has unexpected args: {self.kw}"
            return type(self)(self.func, self.scope, kw)
        if kw:
            raise NotImplementedError(
                "Applying a fixture to a function with additional fixture "
                "arguments is not implemented. Please submit a feature "
                "request if there is a valid use case."
            )
        return use(self)(function)

    def _register(self, request):
        request.session._fixturemanager._register_fixture(
            name=self._id,
            func=self.get_generator(),
            nodeid=request.node.nodeid,
            scope=self.scope,
        )

    def get_generator(self):
        if is_generator(self.func) and not self.kw:
            return self.func
        return _yield_from(self.func, self.kw)


def _get_value(fixture, scope):
    if scope != "function":
        raise NotImplementedError("TODO test")
    if isinstance(fixture, UnmagicFixture):
        return fixture.get_value()
    if getfixturemarker(fixture) is not None:
        return get_fixture_value(fixture.__name__)
    if not hasattr(type(fixture), "__enter__"):
        fixture = fixture()
    if hasattr(type(fixture), "__enter__"):
        def func():
            with fixture as value:
                yield value
        return UnmagicFixture(func, scope).get_value()
    raise ValueError(f"{fixture} is not a fixture")


def _yield_from(func, kwargs):
    @wraps(func)
    def fixture_generator(*args, **kw):
        if kwargs:
            kw = kwargs | kw
        gen = func(*args, **kw)
        if not isinstance(gen, GeneratorType):
            raise TypeError(f"fixture {func.__name__!r} does not yield")
        yield from gen
    return fixture_generator
