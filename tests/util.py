import inspect
import textwrap


def get_source(func):
    src = inspect.getsource(func)
    while True:
        firstline, src = src.split("\n", 1)
        if f'def {func.__name__}(' in firstline:
            return textwrap.dedent(src)
        assert src
