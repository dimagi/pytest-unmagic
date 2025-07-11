# flake8: noqa: F401
from _pytest.compat import (
    get_real_func,
    safe_getattr,
    safe_isclass,
)
from _pytest.fixtures import (
    _get_direct_parametrize_args as get_direct_parametrize_args,
    getfixturemarker,
)
from _pytest.pathlib import bestrelpath


def get_arg_names(item):
    # _pytest.fixtures: Not all items have _fixtureinfo attribute.
    info = getattr(item, "_fixtureinfo", None)
    return info.argnames if info is not None else []


def get_request(item):
    return item._request


def getfixturedefs(node, unmagic_id):
    return node.session._fixturemanager.getfixturedefs(unmagic_id, node)


def register_fixture(session, **kw):
    return session._fixturemanager._register_fixture(**kw)
