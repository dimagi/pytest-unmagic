"""Simple unmagical fixture decorators

Unmagic fixtures use standard Python import semantics, making their
origins more intuitive.
"""
from functools import cached_property, wraps
from inspect import Parameter, ismethod, signature
from os.path import dirname
from types import GeneratorType

import pytest
from _pytest.compat import is_generator
from _pytest.fixtures import getfixturemarker

from .scope import get_request

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
    a lower scope to retrieve the value of the fixture.
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
                fixture_args = [f.get_value() for f in unmagics]
                if args and ismethod(getattr(get_request(), "function", None)):
                    # retain self as first argument
                    fixture_args.insert(0, args[0])
                    args = args[1:]
                if len(fixture_args) > num_params:
                    fixture_args = fixture_args[:num_params]
            except Exception as exc:
                pytest.fail(f"fixture setup for {func.__name__!r} failed: "
                            f"{type(exc).__name__}: {exc}")
            return func(*fixture_args, *args, **kw)

        unmagics = [UnmagicFixture.create(f) for f in fixtures]
        seen = set(unmagics)
        subs = [sub
                for fix in unmagics
                for sub in getattr(fix, "unmagic_fixtures", [])
                if sub not in seen and (seen.add(sub) or True)]
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
    _pytestfixturefunction = True

    @classmethod
    def create(cls, fixture, scope="function"):
        if scope != "function":
            raise NotImplementedError("TODO test")
        if isinstance(fixture, cls):
            return fixture
        if getfixturemarker(fixture) is not None:
            def func():
                yield get_fixture_value(fixture.__name__)
            # do not use @wraps(fixture) to prevent pytest from
            # introspecting arguments from wrapped function
            func.__name__ = fixture.__name__
            func.wrapped = fixture
        else:
            outer = fixture
            if callable(fixture) and not hasattr(type(fixture), "__enter__"):
                fixture = fixture()
            if hasattr(type(fixture), "__enter__"):
                def func():
                    with fixture as value:
                        yield value
                # do not use @wraps(fixture) to prevent pytest from
                # introspecting arguments from wrapped function
                func.__name__ = type(fixture).__name__
                func.wrapped = outer
            else:
                raise ValueError(f"{fixture} is not a fixture")
        return cls(func, scope)

    def __init__(self, func, scope, kw=None):
        self.scope = scope
        self.func = func
        self.kw = kw

    def get_value(self):
        request = get_request()
        if not self._is_registered_for(request.node):
            self._register(request.node)
        return request.getfixturevalue(self._id)

    @cached_property
    def _id(self):
        return f"unmagic-{self.__name__}-{hex(hash(self))[2:]}"

    @property
    def unmagic_fixtures(self):
        return getattr(self.func, "unmagic_fixtures")

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

    def _is_registered_for(self, node):
        return node.session._fixturemanager.getfixturedefs(self._id, node)

    def _register(self, node):
        node.session._fixturemanager._register_fixture(
            name=self._id,
            func=self.get_generator(),
            nodeid=_SCOPE_NODE_ID[self.scope](node.nodeid),
            scope=self.scope,
        )

    def get_generator(self):
        if is_generator(self.func) and not self.kw:
            return self.func
        return _yield_from(self.func, self.kw)


_SCOPE_NODE_ID = {
    "function": lambda n: n,
    "class": lambda n: n.rsplit("::", 1)[0],
    "module": lambda n: n.split("::", 1)[0],
    "package": lambda n: dirname(n.split("::", 1)[0]),
    "session": lambda n: "",
}


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
