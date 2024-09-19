import inspect
import textwrap
from contextlib import contextmanager
from unittest.mock import patch

import _pytest.pytester as _pytester
from unmagic import fixture, use
from unmagic.scope import get_active, set_active


def get_source(func):
    src = inspect.getsource(func)
    while True:
        firstline, src = src.split("\n", 1)
        if f'def {func.__name__}(' in firstline:
            return textwrap.dedent(src)
        assert src


@fixture
@use(_pytester.pytester)
def unmagic_tester(pytester):
    with patch.object(_pytester, "main", unmagic_inactive()(_pytester.main)):
        yield pytester


@contextmanager
def unmagic_inactive():
    obj = get_active()
    set_active(None)
    try:
        yield
    finally:
        set_active(obj)
