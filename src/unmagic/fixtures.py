"""Simple unmagical fixture decorators

Unmagical fixtures make it obvious where a fixture comes from using
standard Python import semantics.
"""
from functools import wraps
from inspect import signature
from contextlib import contextmanager, ExitStack

__all__ = ["fixture", "use"]


def fixture(func):
    """Unmagic fixture decorator

    Facilitates fixture value caching/sharing among fixtures used by a test.
    """
    @wraps(func)
    @contextmanager
    def fixture_context(*args, _unmagic_fixtures=None, **kw):
        if (getattr(func, "has_unmagic_fixtures", False)
                and _unmagic_fixtures is not None):
            return func(*args, _unmagic_fixtures=_unmagic_fixtures, **kw)
        return func(*args, **kw)

    fixture_context.accepts_unmagic_fixtures = True
    fixture_context.__test__ = False
    return fixture_context


def use(*fixtures):
    """Apply fixture(s) to a function

    Fixtures are passed to the function as positional arguments in the
    same order as they were passed to this decorator factory. Additional
    arguments passed to decorated functions are applied after fixtures.

    Any context manager may be used as a fixture. However the unmagic
    ``@fixture`` decorator is especially handy because it facilitates
    fixture value caching/sharing for a graph of fixtures used by a
    test.
    """
    if not fixtures:
        raise TypeError("At least one fixture is required")

    def apply_fixtures(func):
        @wraps(func)
        def run_with_fixtures(*args, _unmagic_fixtures=None, **kw):
            with ExitStack() as stack:
                cache = {} if _unmagic_fixtures is None else _unmagic_fixtures
                fixture_args = []
                for fixture in fixtures:
                    if fixture in cache:
                        value = cache[fixture]
                    elif getattr(fixture, "accepts_unmagic_fixtures", False):
                        context = fixture(_unmagic_fixtures=cache)
                        value = cache[fixture] = stack.enter_context(context)
                    else:
                        value = cache[fixture] = stack.enter_context(fixture())
                    fixture_args.append(value)
                return func(*fixture_args, *args, **kw)

        run_with_fixtures.has_unmagic_fixtures = True
        sig = signature(func)
        new_params = list(sig.parameters.values())[len(fixtures):]
        func.__signature__ = sig.replace(parameters=new_params)
        return run_with_fixtures
    return apply_fixtures
