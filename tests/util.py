import inspect
import textwrap
from contextlib import contextmanager
from unittest.mock import patch

import _pytest.pytester as _pytester
from unmagic import fixture
from unmagic.scope import get_active, get_request, set_active


def get_source(func):
    src = inspect.getsource(func)
    while True:
        firstline, src = src.split("\n", 1)
        if f'def {func.__name__}(' in firstline:
            return textwrap.dedent(src)
        assert src


@fixture
def unmagic_tester():
    with patch.object(_pytester, "main", unmagic_inactive()(_pytester.main)):
        yield get_request().getfixturevalue("pytester")


@contextmanager
def unmagic_inactive():
    obj = get_active()
    set_active(None)
    try:
        yield
    finally:
        set_active(obj)
