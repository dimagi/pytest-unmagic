from functools import partial
from pathlib import Path

from . import _api
from .scope import get_active


def autouse(fixture, /, where=None):
    """Register fixture setup within a qualified scope

    The fixture will be set up each time its scope is entered at the
    beginning of or within the qualified scope and torn down at the end
    of its scope.

    When used as a decorator the ``where`` value should be passed as the
    first argument. For example: ``@autouse(__file__)``

    :param fixture: An unmagic fixture.
    :param where: Scope qualifier such as a module's or package's
        ``__file__``. Fixture setup will run when the first test within
        the qualified scope is run.
    """
    if where is None:
        if not isinstance(fixture, str):
            raise ValueError(
                f"autouse decorator requires a location (got: {fixture})")
        return partial(autouse, where=fixture)

    session = get_active().session
    path = Path(where)
    if path.name == "__init__.py":
        path = path.parent
    nodeid = _api.bestrelpath(session.config.invocation_params.dir, path)
    _api.register_fixture(
        session,
        name=f"{nodeid}::{fixture.__name__}",
        func=fixture.get_generator(),
        nodeid=nodeid,
        scope=fixture.scope,
        autouse=True,
    )
    return fixture
