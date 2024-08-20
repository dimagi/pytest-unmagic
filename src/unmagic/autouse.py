from functools import partial
from pathlib import Path

from _pytest.pathlib import bestrelpath

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

    def func():
        with fixture() as value:
            yield value

    session = get_active().session
    path = Path(where)
    if path.name == "__init__.py":
        path = path.parent
    nodeid = bestrelpath(session.config.invocation_params.dir, path)
    session._fixturemanager._register_fixture(
        name=f"{nodeid}::{fixture.__name__}",
        func=func,
        nodeid=nodeid,
        scope=fixture.scope,
        autouse=True,
    )
    return fixture
