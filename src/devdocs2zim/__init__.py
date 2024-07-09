# pyright: strict, reportUnnecessaryIsInstance=false

from devdocs2zim.__about__ import __version__


def compute(a: int, b: int) -> int:
    if not isinstance(a, int) or not isinstance(b, int):
        msg = "int only"
        raise TypeError(msg)
    return a + b


def entrypoint():
    print(f"Hello from {__version__}")  # noqa: T201
