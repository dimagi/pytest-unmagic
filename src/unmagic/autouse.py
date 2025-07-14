import warnings
from inspect import isgeneratorfunction
from pathlib import Path

from . import _api
from .scope import get_active

# autouse fixtures may be discovered when a plugin or conftest
# module is imported before the session has started
_early_autouses = []


def autouse(fixture, where):
    """Register fixture setup within a qualified scope

    The fixture will be set up each time its scope is entered at the
    beginning of or within the qualified scope and torn down at the end
    of its scope. For example, a class-scoped fixture will be setup and
    torn down for each test class within a module when the fixture is
    registered in the module with ``autouse(class_fixture, __file__)``.
    Autouse within a package can be registered with ``__file__`` in the
    ``__init__.py`` module of the package.

    :param fixture: An unmagic fixture.
    :param where: Scope qualifier such as a module's or package's
        ``__file__``. Fixture setup will run when the first test within
        the qualified scope is run. If ``True``, apply to all tests in
        the session.
    """
    active = get_active()
    if active is None:
        _early_autouses.append((fixture, where))
    else:
        _register_autouse(fixture, where, active.session)
        if active.request is not None:
            warnings.warn(
                "autouse fixture registered while running tests. "
                "Relevant tests may have already been run."
            )


def _register_early_autouses(session):
    while _early_autouses:
        fixture, where = _early_autouses.pop()
        _register_autouse(fixture, where, session)


def _register_autouse(fixture, where, session):
    if where is True:
        nodeid = ""
    else:
        path = Path(where)
        if path.name == "__init__.py":
            path = path.parent
        nodeid = _api.bestrelpath(session.config.invocation_params.dir, path)
    assert isgeneratorfunction(fixture.func), repr(fixture)
    _api.register_fixture(
        session,
        name=f"{nodeid}::{fixture._id}",
        func=fixture.func,
        nodeid=nodeid,
        scope=fixture.scope,
        autouse=True,
    )
    return fixture
